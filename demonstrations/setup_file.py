import sys
sys.path.extend(['/data1/zhengye/MultipathBP', '/data1/zhengye/MultipathBP'])
import torch
import torch.nn as nn
import torchvision
import time

from multipath_bp.bound_general_multipath import BoundedModule
from multipath_bp import BoundedTensor
from multipath_bp.perturbations_multipath import PerturbationLpNorm

### Step 1: load model and dataset
def mnist_ffnn():
    model = nn.Sequential(
        nn.Linear(784, 80),
        nn.ReLU(),
        nn.Linear(80, 80),
        nn.ReLU(),
        nn.Linear(80, 80),
        nn.ReLU(),
        nn.Linear(80, 80),
        nn.ReLU(),
        nn.Linear(80, 80),
        nn.ReLU(),
        nn.Linear(80, 80),
        nn.ReLU(),
        nn.Linear(80, 80),
        nn.ReLU(),
        nn.Linear(80, 80),
        nn.ReLU(),
        nn.Linear(80, 80),
        nn.ReLU(),
        nn.Linear(80, 80),
        nn.ReLU(),
        nn.Linear(80, 10)
    )
    return model
checkpoint = torch.load("./mnist_ffnn_10x80.pth", map_location=torch.device('cpu'))
test_data = torchvision.datasets.MNIST("../examples/vision/data", train=False, download=False, transform=torchvision.transforms.ToTensor())
#########


model = mnist_ffnn()
model.load_state_dict(checkpoint)
N = 1
n_classes = 10
image = test_data.data[:N].reshape(N, 784)
image = image.to(torch.float32) / 255.0
true_label = test_data.targets[:N]
if torch.cuda.is_available():
    image = image.cuda()
    model = model.cuda()
print('Running on', image.device)
time_begin = time.time()


### Step 2: wrap model with MultipathBP
lirpa_model = BoundedModule(model, torch.empty_like(image), device=image.device)
#########


### Step 3: set specification
delta = 0.010
norm = float("inf")
#########


ptb = PerturbationLpNorm(norm=norm, eps=delta)
image = BoundedTensor(image, ptb)
pred = lirpa_model(image)
label = torch.argmax(pred, dim=1).cpu().detach().numpy()
lirpa_model = BoundedModule(model, torch.empty_like(image), device=image.device)


### Step 4: compute reachable region
method = 'backward'
#########


print("Bounding method:", method)
print('')
print('=============== Reachable region ===============')
lb, ub = lirpa_model.compute_bounds(x=(image,), method=method.split()[0])
for i in range(N):
    print("Image {} top-1 prediction {} ground-truth {}".format(i, label[i], true_label[i]))
    for j in range(n_classes):
        indicator = '(ground-truth)' if j == true_label[i] else ''
        print("f_{j}(x_0): {l:8.3f} <= f_{j}(x_0+delta) <= {u:8.3f} {ind}".format(
            j=j, l=lb[i][j].item(), u=ub[i][j].item(), ind=indicator))











### specification matrix
C = torch.zeros(size=(N, n_classes - 1, n_classes), device=image.device)
groundtruth = true_label.to(device=image.device).unsqueeze(1).unsqueeze(1)
C.scatter_(dim=2, index=groundtruth.repeat(1, n_classes - 1, 1), value=1.0)
target_labels = torch.arange(1, 10, device=image.device).repeat(N, 1, 1).transpose(1, 2)
target_labels = (target_labels + groundtruth) % n_classes
C.scatter_(dim=2, index=target_labels, value=-1.0)
# print('Computing bounds with a specification matrix:\n', C)

lb, ub = lirpa_model.compute_bounds(x=(image,), method=method.split()[0], C=C)
verified_robust = 0
for i in range(N):
    if torch.min(lb, dim=1)[0][i] >= 0:
        verified_robust += 1
time_elapse = time.time() - time_begin
print('')
print('================== Robustness ==================')
print('verified') if verified_robust == 1 else print('unknown')
print('Time elapsed:', time_elapse)