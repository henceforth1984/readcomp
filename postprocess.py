#!/usr/bin/env python
from __future__ import unicode_literals

import numpy as np
import h5py
import argparse
import sys
import re
import codecs
import copy
import operator
import json
import glob, os, fnmatch
import csv
import re
import time
import seaborn as sns
import matplotlib.pyplot as plt
import datamodel
from pylab import savefig

args = {}


def compute_accuracy(args):
  total = 0
  total_context = 0 # answer is in context
  correct = 0
  for filename in glob.glob(args.model_dump_pattern):
    with h5py.File(filename, "r") as f:
      inputs      = np.array(f['inputs'],      dtype=int)
      targets     = np.array(f['targets'],     dtype=int)
      outputs     = np.array(f['outputs'],     dtype=float)
      predictions = np.array(f['predictions'], dtype=int)
      answers     = np.array(f['answers'],     dtype=int)

      batch_size, max_len = outputs.shape
      answer_index = answers > 0
      total += np.sum(answer_index)
      total_context += np.sum([1 if answers[b] > 0 and answers[b] in inputs.T[b] else 0 for b in range(batch_size)])
      correct += np.sum(predictions[answer_index] == answers[answer_index])

  print 'Correct = {}, Total = {}, % = {:.4f}%, Total Context = {}, % = {:.4f}%'.format(
    correct, total, float(correct) * 100 / total, total_context, float(correct) * 100 / total_context)


def main(arguments):
  global args
  parser = argparse.ArgumentParser(
      description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter) 
  parser.add_argument('--model_dump_pattern', type=str, default='data\\dump\\*.dump',
                      help='file pattern of model dumps for analysis')
  parser.add_argument('--out_vocab_file_prefix', type=str, default='lambada-asr',
                      help='file name prefix of vocab files')
  parser.add_argument('--in_context_only', action='store_true',
                      help='whether to process only instances where answer is in context')
  parser.add_argument('--verbose_level', type=int, default=2,
                      help='level of verbosity, ranging from 0 to 2, default = 2')

  args = parser.parse_args(arguments)

  hfont = { 'fontname':'serif' }
  sns.set(font_scale=2,font='serif')
  plt.figure(figsize=(54, 24), dpi=100)

  compute_accuracy(args)

  corpus = datamodel.Corpus(args.verbose_level, None, None, None, None, None, None, None, None)
  corpus.load_vocab(args.out_vocab_file_prefix)
  idx2word = corpus.dictionary.idx2word

  for filename in glob.glob(args.model_dump_pattern):
    with h5py.File(filename, "r") as f:
      inputs      = np.array(f['inputs'],      dtype=int)
      targets     = np.array(f['targets'],     dtype=int)
      outputs     = np.array(f['outputs'],     dtype=float)
      predictions = np.array(f['predictions'], dtype=int)
      answers     = np.array(f['answers'],     dtype=int)

      batch_size, max_len = outputs.shape
      dim1 = int(np.floor(np.sqrt(max_len)))
      dim2 = int(np.ceil(float(max_len) / dim1))

      ip = np.concatenate((inputs.T, np.zeros((batch_size, dim1 * dim2 - max_len))), axis = 1)
      op = np.concatenate((outputs,  np.zeros((batch_size, dim1 * dim2 - max_len))), axis = 1)

      txt = []
      for i in range(ip.shape[0]):
        r = []
        for j in range(ip.shape[1]):
          word = idx2word[int(ip[i,j])] if ip[i,j] != 0 else ''
          r.append(u'{}\n{:.4f}'.format(word, op[i,j]))
        txt.append(np.array(r))
      labels = np.array(txt)

      for b in range(batch_size):
        if answers[b] != 0:
          if args.in_context_only and answers[b] not in ip[b]:
            continue
          ax = plt.axes()
          sns.heatmap(op[b].reshape((dim1,dim2)), annot=labels[b].reshape((dim1,dim2)), fmt='', cmap='Blues', ax = ax)
          answer_indicator = r"$\bf{CORRECT}$" if answers[b] == predictions[b] else "Correct"
          answer_indicator = answer_indicator + ' (in context)' if answers[b] in ip[b] else answer_indicator
          target_sentence = ' '.join([idx2word[idx] if idx != 0 else '' for idx in targets[:,b]]).strip()
          ax.set_title('{} = {}, Prediction = {}\nTarget = {}'.format(answer_indicator, idx2word[answers[b]], idx2word[predictions[b]], target_sentence))
          # plt.show()
          savefig(filename + '.ex{}.png'.format(str(b).zfill(3)), bbox_inches='tight', dpi = 100)
          plt.clf()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
