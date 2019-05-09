'''
/* ===========================================================================
** Copyright (C) 2019 Infineon Technologies AG. All rights reserved.
** ===========================================================================
**
** ===========================================================================
** Infineon Technologies AG (INFINEON) is supplying this file for use
** exclusively with Infineon's sensor products. This file can be freely
** distributed within development tools and software supporting such 
** products.
** 
** THIS SOFTWARE IS PROVIDED "AS IS".  NO WARRANTIES, WHETHER EXPRESS, IMPLIED
** OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, IMPLIED WARRANTIES OF
** MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE APPLY TO THIS SOFTWARE.
** INFINEON SHALL NOT, IN ANY CIRCUMSTANCES, BE LIABLE FOR DIRECT, INDIRECT, 
** INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES, FOR ANY REASON 
** WHATSOEVER.
** ===========================================================================
*/
'''


import torch.utils.data as data

import random
from PIL import Image
import os
import os.path
import numpy as np
from numpy.random import randint

class VideoRecord(object):
    def __init__(self, row):
        self._data = row

    @property
    def path(self):
        return self._data[0]

    @property
    def num_frames(self):
        return int(self._data[1])

    @property
    def label(self):
        return int(self._data[2])


class DataSet(data.Dataset):
    def __init__(self, root_path, list_file,
                 num_segments=3, modality='RGB',
                 image_tmpl='img_{:05d}.jpg', transform=None,
                 random_shift=True,
                 test_mode=False, dataset='jester'):

        self.root_path = root_path
        self.list_file = list_file
        self.num_segments = num_segments
        self.modality = modality
        self.image_tmpl = image_tmpl
        self.transform = transform
        self.random_shift = random_shift
        self.test_mode = test_mode
        self.dataset = dataset


        self._parse_list()

    def _load_image(self, directory, idx):
        try:
            return [Image.open(os.path.join(self.root_path, directory, self.image_tmpl.format(idx))).convert('RGB')] 
        except Exception:
            print('error loading image:', os.path.join(self.root_path, directory, self.image_tmpl.format(idx)))
            return [Image.open(os.path.join(self.root_path, directory, self.image_tmpl.format(1))).convert('RGB')]

    def _parse_list(self):
        # check the frame number is large >3:
        # usualy it is [video_id, num_frames, class_idx]
        tmp = [x.strip().split(' ') for x in open(self.list_file)]
        tmp = [item for item in tmp if int(item[1])>=3]
        self.video_list = [VideoRecord(item) for item in tmp]
        print('video number:%d'%(len(self.video_list)))

    def _sample_indices(self, record):
        """
        :param record: VideoRecord
        :return: list
        """
        average_duration = (record.num_frames) // self.num_segments

        if average_duration > 0:
            offsets = np.multiply(list(range(self.num_segments)), average_duration) + randint(average_duration, size=self.num_segments)
        elif record.num_frames > self.num_segments:
            offsets = np.sort(randint(record.num_frames , size=self.num_segments))
        else:
            offsets = np.zeros((self.num_segments,))
        return offsets + 1

    def _get_val_indices(self, record):
        if record.num_frames > self.num_segments :
            tick = (record.num_frames) / float(self.num_segments)
            offsets = np.array([int(tick / 2.0 + tick * x) for x in range(self.num_segments)])
        else:
            offsets = np.zeros((self.num_segments,))
        return offsets + 1

    def _get_test_indices(self, record):
        tick = (record.num_frames ) / float(self.num_segments)
        offsets = np.array([int(tick / 2.0 + tick * x) for x in range(self.num_segments)])
        return offsets + 1


    def __getitem__(self, index):
        record = self.video_list[index]
        # check this is a legit video folder
        if (self.modality == 'IRD' or self.modality == 'D' or self.modality == 'IR'):
            while not os.path.exists(os.path.join(self.root_path, "Grayscale", record.path, (self.image_tmpl.format(0)))):
                index = np.random.randint(len(self.video_list))
                record = self.video_list[index]

        else:
            while not os.path.exists(os.path.join(self.root_path, record.path, self.image_tmpl.format(1))):
                index = np.random.randint(len(self.video_list))
                record = self.video_list[index]

        if not self.test_mode:
            segment_indices = self._sample_indices(record) if self.random_shift else self._get_val_indices(record)
        else:
            segment_indices = self._get_test_indices(record)

        return self.get(record, segment_indices)

    def get(self, record, indices):
        images = list()
        for seg_ind in indices:
            p = int(seg_ind)
            seg_imgs = self._load_image(record.path, p)
            images.extend(seg_imgs)

        process_data = self.transform(images)

        return process_data, record.label
        

    def __len__(self):
        return len(self.video_list)
