import torch
import torch.nn as nn
import torch.nn.init as init
import torch.nn.functional as F
import math
from models import vgg


class EAST(nn.Module):
    """East is the east network

    """

    def __init__(self, lock_vgg=False):
        super(EAST, self).__init__()

        # conv1

        self.conv1_1 = nn.Conv2d(3, 64, 3, padding=1)
        self.relu1_1 = nn.ReLU(inplace=True)
        self.conv1_2 = nn.Conv2d(64, 64, 3, padding=1)
        self.relu1_2 = nn.ReLU(inplace=True)
        self.pool1 = nn.MaxPool2d(2, stride=2, ceil_mode=True)  # 1/2

        # conv2

        self.conv2_1 = nn.Conv2d(64, 128, 3, padding=1)
        self.relu2_1 = nn.ReLU(inplace=True)
        self.conv2_2 = nn.Conv2d(128, 128, 3, padding=1)
        self.relu2_2 = nn.ReLU(inplace=True)
        self.pool2 = nn.MaxPool2d(2, stride=2, ceil_mode=True)  # 1/4

        # conv3
        self.conv3_1 = nn.Conv2d(128, 256, 3, padding=1)
        self.relu3_1 = nn.ReLU(inplace=True)
        self.conv3_2 = nn.Conv2d(256, 256, 3, padding=1)
        self.relu3_2 = nn.ReLU(inplace=True)
        self.conv3_3 = nn.Conv2d(256, 256, 3, padding=1)
        self.relu3_3 = nn.ReLU(inplace=True)
        self.pool3 = nn.MaxPool2d(2, stride=2, ceil_mode=True)  # 1/8

        # conv4

        self.conv4_1 = nn.Conv2d(256, 512, 3, padding=1)
        self.relu4_1 = nn.ReLU(inplace=True)
        self.conv4_2 = nn.Conv2d(512, 512, 3, padding=1)
        self.relu4_2 = nn.Conv2d(512, 512, 3, padding=1)
        self.conv4_3 = nn.Conv2d(512, 512, 3, padding=1)
        self.relu4_3 = nn.ReLU(inplace=True)
        self.pool4 = nn.MaxPool2d(2, stride=2, ceil_mode=True)  # 1/16

        # conv5
        self.conv5_1 = nn.Conv2d(512, 512, 3, padding=1)
        self.relu5_1 = nn.ReLU(inplace=True)
        self.conv5_2 = nn.Conv2d(512, 512, 3, padding=1)
        self.relu5_2 = nn.ReLU(inplace=True)
        self.conv5_3 = nn.Conv2d(512, 512, 3, padding=1)
        self.relu5_3 = nn.ReLU(inplace=True)
        self.pool5 = nn.MaxPool2d(2, stride=2, ceil_mode=True)

        # # fc6
        # self.fc6 = nn.Conv2d(512, 4096, 7)
        # self.relu6 = nn.ReLU(inplace=True)
        # self.drop6 = nn.Dropout2d()
        #
        # # fc7
        # self.fc7 = nn.Conv2d(4096, 4096, 1)
        # self.relu7 = nn.ReLU(inplace=True)
        # self.drop7 = nn.Dropout2d()

        layer4 = nn.Sequential(nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(inplace=True))

        layer3 = nn.Sequential(nn.Conv2d(256, 32, 1), nn.BatchNorm2d(32), nn.ReLU(inplace=True),
                               nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(inplace=True))

        layer2 = nn.Sequential(nn.Conv2d(512, 128, 1), nn.BatchNorm2d(128), nn.ReLU(inplace=True),
                               nn.Conv2d(128, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(inplace=True))

        layer1 = nn.Sequential(nn.Conv2d(1024, 256, 1), nn.BatchNorm2d(256), nn.ReLU(inplace=True),
                               nn.Conv2d(256, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(inplace=True))

        self.feature_convs = nn.ModuleList([layer1, layer2, layer3, layer4])
        self.unpools = nn.ModuleList(
            [nn.Upsample(scale_factor=2, mode='bilinear'), nn.Upsample(scale_factor=2, mode='bilinear'),
             nn.Upsample(scale_factor=2, mode='bilinear')])
        self.inside_score_net = nn.Sequential(nn.Conv2d(32, 1, 1), nn.Sigmoid())
        self.side_v_geo = nn.Sequential(nn.Conv2d(32, 4, 1), nn.Sigmoid())
        self.side_v_angle = nn.Sequential(nn.Conv2d(32, 1, 1), nn.Sigmoid())

        self._init_weights()

        vgg16 = vgg.VGG16(pretrained=True)

        self.copy_params_from_vgg16(vgg16)

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                m.weight.data.zero_()
                if m.bias is not None:
                    m.bias.data.zero_()

    def copy_params_from_vgg16(self, vgg16):
        features = [
            self.conv1_1, self.relu1_1,
            self.conv1_2, self.relu1_2,
            self.pool1,
            self.conv2_1, self.relu2_1,
            self.conv2_2, self.relu2_2,
            self.pool2,
            self.conv3_1, self.relu3_1,
            self.conv3_2, self.relu3_2,
            self.conv3_3, self.relu3_3,
            self.pool3,
            self.conv4_1, self.relu4_1,
            self.conv4_2, self.relu4_2,
            self.conv4_3, self.relu4_3,
            self.pool4,
            self.conv5_1, self.relu5_1,
            self.conv5_2, self.relu5_2,
            self.conv5_3, self.relu5_3,
            self.pool5,
        ]

        for l1, l2 in zip(vgg16.features, features):
            if isinstance(l1, nn.Conv2d) and isinstance(l2, nn.Conv2d):
                print(l1, l2)
                assert l1.weight.size() == l2.weight.size()
                assert l1.bias.size() == l2.bias.size()
                l2.weight.data = l1.weight.data
                l2.bias.data = l1.bias.data

    def forward(self, x):
        h = x
        h = self.relu1_1(self.conv1_1(h))
        h = self.relu1_2(self.conv1_2(h))
        h = self.pool1(h)

        h = self.relu2_1(self.conv2_1(h))
        h = self.relu2_2(self.conv2_2(h))
        h = self.pool2(h)

        pool2 = h
        h = self.relu3_1(self.conv3_1(h))
        h = self.relu3_2(self.conv3_2(h))
        h = self.relu3_3(self.conv3_3(h))
        h = self.pool3(h)

        pool3 = h
        h = self.relu4_1(self.conv4_1(h))
        h = self.relu4_2(self.conv4_2(h))
        h = self.relu4_3(self.conv4_3(h))
        h = self.pool4(h)

        pool4 = h
        h = self.relu5_1(self.conv5_1(h))
        h = self.relu5_2(self.conv5_2(h))
        h = self.relu5_3(self.conv5_3(h))
        h = self.pool5(h)

        pool5 = h
        f = [pool5, pool4, pool3, pool2]

        g = [None, None, None, None]
        h = [None, None, None, None]

        for i in range(4):
            if i == 0:
                h[i] = f[i]
            else:
                concat = torch.cat([g[i - 1], f[i]], dim=1)
                h[i] = self.feature_convs[i - 1](concat)
            if i <= 2:
                g[i] = self.unpools[i - 1](h[i])
            else:

                g[i] = self.feature_convs[i](h[i])
        F_score = self.inside_score_net(g[3])

        geo_map = self.side_v_geo(g[3]) * 512

        angle_map = self.side_v_angle(g[3])

        angle_map = (angle_map - 0.5) * math.pi / 2

        F_geometry = torch.cat((geo_map, angle_map), dim=1)
        return F_score, F_geometry

