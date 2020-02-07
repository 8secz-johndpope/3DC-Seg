import glob
import os
import numpy as np
from PIL import Image

from util import save_mask

# data_dir = '/home/mahadevan/vision/external_algorithms/rgmp/rgmp_kitti/RGMP_results/MO-USUP-update-refs-testdev/'
data_dir = '/globalwork/data/DAVIS-Unsupervised/DAVIS/flo_warped_tracks/'
out_dir = 'results/eval_maskrcnn_warp/davis-val/'


def main():
  seqs = glob.glob(data_dir + "/*")
  for seq in seqs:
    result_files = glob.glob(os.path.join(data_dir, seq, "*.png"))
    for result_file in result_files:
      image = np.array(Image.open(result_file).convert("P"))
      if np.max(image) > 20:
        print("{} has values greater than 20".format(result_file))
        image[image > 20] = 0
      out_dir_updated = os.path.join(out_dir, "updated_index", seq.split('/')[-1])
      if not os.path.exists(out_dir_updated):
        os.makedirs(out_dir_updated)
      save_mask(image, os.path.join(out_dir_updated, os.path.basename(result_file)))


if __name__ == '__main__':
    main()