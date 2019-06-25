from .base import BaseVectorizer
from .base import BaseTextU
from .base import BasePair

from .common import DummyPreprocessor as PaddleBowPreprocessor
from .common import JiebaTokenizer as PaddleBowAnalyzer
from .ann import Ann

import paddle
import paddle.fluid as fluid

import os
import numpy as np


class PaddleBowVectorizer(BaseVectorizer):
    def __init__(self, vocab_file):
        self._vocab = self._load_vocab(vocab_file)


    def _load_vocab(self, file_path):
    	"""
    	load the given vocabulary
    	"""
    	vocab = {}
    	if not os.path.isfile(file_path):
    	    raise ValueError("vocabulary dose not exist under %s" % file_path)
    	with open(file_path, 'r') as f:
    	    for line in f:
    	        items = line.strip('\n').split("\t")
    	        if items[0] not in vocab:
    	            vocab[items[0]] = int(items[1])
    	vocab["<unk>"] = 0
    	return vocab

    def transform(self, ares):
        words = ares
        vec = [self._vocab[word] for word in words if word in self._vocab]
        if len(vec) == 0:
            vec = [0]

        return vec


class PaddleBowTextU(BaseTextU):
    def __init__(self, vocab_file):
        preprocessor = PaddleBowPreprocessor()
        analyzer = PaddleBowAnalyzer()
        vectorizer = PaddleBowVectorizer(vocab_file)
        super(PaddleBowTextU, self).__init__(preprocessor = preprocessor,
                                          analyzer = analyzer,
                                          vectorizer = vectorizer
                                         )


class PaddleBowSim(BasePair):
    def __init__(self, vocab_file, model_path,
                 use_cuda = False,
                 task_mode = 'pairwise'
                ):
        self.task_mode = task_mode
        textu = PaddleBowTextU(vocab_file)
        if use_cuda:
            place = fluid.CUDAPlace(0)
        else:
            place = fluid.CPUPlace()

        self.executor = fluid.Executor(place=place)
        self.program, self.feed_var_names, self.fetch_targets = fluid.io.load_inference_model( model_path, self.executor)
        self.infer_feeder = fluid.DataFeeder( place=place, feed_list=self.feed_var_names, program=self.program)
        super(PaddleBowSim, self).__init__(textu = textu)

    def transform(self, vec1, vec2):
        output = self.executor.run(self.program,
                                   feed=self.infer_feeder.feed([[vec1, vec2]]),
                                   fetch_list=self.fetch_targets)
        if self.task_mode == 'pairwise':
            score = list( map(lambda item: (item[0] + 1) / 2, output[1]))[0]
        else:
            score = list(map(lambda item: np.argmax(item), output[1]))[0]
        return score

