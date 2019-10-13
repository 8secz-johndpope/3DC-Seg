import os
from collections import OrderedDict
import numpy as np
import torch
from PIL import Image
from utils.Constants import font
from utils.util import ToLabel


def load_weights(model, optimizer, args, model_dir, scheduler):
    start_epoch = 0
    best_iou_train = 0
    best_iou_eval = 0
    best_loss_train = 0
    best_loss_eval = 0
    loadepoch = args.loadepoch
    state = model.state_dict()
    # load saved model if specified
    if loadepoch is not None:
      print('Loading checkpoint {}@Epoch {}{}...'.format(font.BOLD, loadepoch, font.END))
      if loadepoch == 'siam':
        # transform, checkpoint provided by RGMP
        load_name2d = 'saved_models/rgmp.pth'
        load_name3d = 'saved_models/resnet-50-kinetics.pth'
        load_name = {1: 'saved_models/youtubevos_pretrain.pth', 2: 'saved_models/rgmp.pth'}
        checkpoint2d = torch.load(load_name2d)
        checkpoint = load_pretrained_weights(load_name3d)
        encoder2d_dict = OrderedDict([(k.lower().replace('module.encoder', 'module.encoder2d'), v)
                                            for k, v in checkpoint2d.items() if "module.encoder" in k.lower()])
        #FIXME: uncomment for using rgmp pretrained weights
        #checkpoint['model'].update(encoder2d_dict)
        # checkpoint = {"model": OrderedDict([(k.replace("module.", ""), v) for k, v in checkpoint.items()])}
      elif loadepoch == 'kinetics':
        # transform, checkpoint provided by RGMP
        load_name = 'saved_models/resnet-50-kinetics.pth'
        checkpoint = torch.load(load_name)
        # checkpoint = {"model": OrderedDict([(k.replace("module.", ""), v) for k, v in checkpoint.items()])}
        checkpoint = {"model": OrderedDict([(k.lower().replace('module.', 'module.encoder.'), v)
                                            for k, v in checkpoint['state_dict'].items()]), 'epoch': 0}
      elif 'pretrain' in loadepoch:
        load_name = os.path.join('saved_models', loadepoch + '.pth')
        checkpoint = load_pretrained_weights(load_name)
      else:
        load_name = os.path.join(model_dir,
                                 '{}.pth'.format(loadepoch))
        checkpoint = torch.load(load_name)
        start_epoch = checkpoint['epoch'] + 1 if args.task == "train" else 0
        # checkpoint["model"] = OrderedDict([(k.replace("module.", ""), v) for k, v in checkpoint["model"].items()])
      checkpoint_valid = {k: v for k, v in checkpoint['model'].items() if k in state and state[k].shape == v.shape}
      missing_keys = np.setdiff1d(list(state.keys()),list(checkpoint_valid.keys()))
      
      if len(missing_keys) > 0:
        print("WARN: {} keys are found missing in the loaded model weights.".format(missing_keys))
      for key in missing_keys:
        checkpoint_valid[key] = state[key]

      model.load_state_dict(checkpoint_valid)
      if args.task == 'train':
        if 'optimizer' in checkpoint.keys() :
          optimizer.load_state_dict(checkpoint['optimizer'])
          lr = optimizer.param_groups[0]['lr']
        if 'scheduler' in checkpoint.keys() and checkpoint['scheduler'] is not None and scheduler is not None:
          scheduler.load_state_dict(checkpoint['scheduler'].state_dict())
        if 'best_iou' in checkpoint.keys() and checkpoint['task'] == 'train':
          best_iou_train = checkpoint['best_iou']
          best_loss_train = checkpoint['loss']
        elif 'best_iou' in checkpoint.keys():
          best_iou_eval = checkpoint['best_iou']
          best_loss_eval = checkpoint['loss']

      del checkpoint
      torch.cuda.empty_cache()
      print('Loaded weights from {}'.format(load_name))

    return model, optimizer, start_epoch, best_iou_train, best_iou_eval, best_loss_train, best_loss_eval


def load_pretrained_weights(load_name):
  checkpoint = torch.load(load_name)
  checkpoint['epoch'] = 0
  keys = ['optimizer', 'scheduler', 'best_iou']
  for key in keys:
    del checkpoint[key]
  return checkpoint


def save_results(all_E, info, num_frames, path, palette):
  if not os.path.exists(path):
    os .makedirs(path)
  for f in range(num_frames):
    E = all_E[0, :, f].numpy()
    # make hard label
    E = ToLabel(E)

    (lh, uh), (lw, uw) = info['pad']
    E = E[lh[0]:-uh[0], lw[0]:-uw[0]]

    img_E = Image.fromarray(E)
    img_E.putpalette(palette)
    img_E.save(os.path.join(path, '{:05d}.png'.format(f)))


def save_checkpoint(epoch, iou_mean, loss_mean, model, optimiser, save_name, is_train, scheduler):
  torch.save({'epoch': epoch,
              'model': model.state_dict(),
              'optimizer': optimiser.state_dict(),
              'best_iou': iou_mean,
              'loss': loss_mean,
              'task': 'train' if is_train else 'eval',
              'scheduler': scheduler
              },
             save_name)
  print("Saving epoch {} with IOU {}".format(epoch, iou_mean))
