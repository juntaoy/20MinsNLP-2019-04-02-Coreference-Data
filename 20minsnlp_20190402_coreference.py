# -*- coding: utf-8 -*-
"""20MinsNLP 20190402-Coreference.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/16hxZTrJS-yvgdeTspDKju2dsVV-TyPY9

# 20Mins NLP: Coreference Resolution
2019-04-02

Welcome to my first session of the 20Mins NLP. In this session we will build a coreference system from scratch. The system is a simplified version of the state-of-the-art Lee et al., (2017) system, which is based on the mention ranking algorithm.

##Obtain the data
In order to run this notebook you will need first download some datasets and pre-trained word embeddings.
"""

!wget http://vectors.nlpl.eu/repository/11/8.zip
!unzip 8.zip
!rm 8.zip 
!git clone https://github.com/juntaoy/20MinsNLP-2019-04-02-Coreference-Data.git

"""##Some help methods
Then we have some help method which make the life easier.

###The shape() method helps us get the n-th dimension of a given tensor.
In tensorflow there are two ways of getting a tensor’s shape. The  `Tensor.get_shape()[n]` method can get a predefined dimension of the tensor,  such as the last dimension of the word_embeddings (300) or the dimension of the hidden layer (for both LSTM and FFNN is 150). The second method (`tf.shape()[n]`) returns the dynamic size of the tensor, such as the number of sentences or the number of mentions. Those sizes are not fixed across different documents thus are dynamic.
"""

def shape(x, n):
  return x.get_shape()[n].value or tf.shape(x)[n]

"""###The time_used() method outputs the time differences between the current time and the input time.
It is always a good practice to record the time usage of individual process, so you always known which part is most expensive to run.
"""

def time_used(start_time):
  curr_time = time.time()
  used_time = curr_time-start_time
  m = used_time // 60
  s = used_time - 60 * m
  return "%d m %d s" % (m, s)

"""###The standard coreference evaluation metric
The code is able to compute the standard coreference evaluation metrics (MUC, B-cubed and Ceafe), and return the CoNLL average score (average F1 of MUC, B-cubed and Ceafe) we needed for evaluating our system.
The code is taken from Lee et al., (2017) system which orignally created by Clark and Manning (2016). You don't have to understand this in order to run the coreference system.
"""

import numpy as np
from collections import Counter
from sklearn.utils.linear_assignment_ import linear_assignment

"""
Mostly borrowed from https://github.com/clarkkev/deep-coref/blob/master/evaluation.py
"""

def f1(p_num, p_den, r_num, r_den, beta=1):
    p = 0 if p_den == 0 else p_num / float(p_den)
    r = 0 if r_den == 0 else r_num / float(r_den)
    return 0 if p + r == 0 else (1 + beta * beta) * p * r / (beta * beta * p + r)

class CorefEvaluator(object):
    def __init__(self):
        self.evaluators = [Evaluator(m) for m in (muc, b_cubed, ceafe)]

    def update(self, predicted, gold, mention_to_predicted, mention_to_gold):
        for e in self.evaluators:
            e.update(predicted, gold, mention_to_predicted, mention_to_gold)

    def get_f1(self):
        return sum(e.get_f1() for e in self.evaluators) / len(self.evaluators)

    def get_recall(self):
        return sum(e.get_recall() for e in self.evaluators) / len(self.evaluators)

    def get_precision(self):
        return sum(e.get_precision() for e in self.evaluators) / len(self.evaluators)

    def get_prf(self):
        return self.get_precision(), self.get_recall(), self.get_f1()

class Evaluator(object):
    def __init__(self, metric, beta=1):
        self.p_num = 0
        self.p_den = 0
        self.r_num = 0
        self.r_den = 0
        self.metric = metric
        self.beta = beta

    def update(self, predicted, gold, mention_to_predicted, mention_to_gold):
        if self.metric == ceafe:
            pn, pd, rn, rd = self.metric(predicted, gold)
        else:
            pn, pd = self.metric(predicted, mention_to_gold)
            rn, rd = self.metric(gold, mention_to_predicted)
        self.p_num += pn
        self.p_den += pd
        self.r_num += rn
        self.r_den += rd

    def get_f1(self):
        return f1(self.p_num, self.p_den, self.r_num, self.r_den, beta=self.beta)

    def get_recall(self):
        return 0 if self.r_num == 0 else self.r_num / float(self.r_den)

    def get_precision(self):
        return 0 if self.p_num == 0 else self.p_num / float(self.p_den)

    def get_prf(self):
        return self.get_precision(), self.get_recall(), self.get_f1()

    def get_counts(self):
        return self.p_num, self.p_den, self.r_num, self.r_den


def evaluate_documents(documents, metric, beta=1):
    evaluator = Evaluator(metric, beta=beta)
    for document in documents:
        evaluator.update(document)
    return evaluator.get_precision(), evaluator.get_recall(), evaluator.get_f1()


def b_cubed(clusters, mention_to_gold):
    num, dem = 0, 0

    for c in clusters:
        if len(c) == 1:
            continue

        gold_counts = Counter()
        correct = 0
        for m in c:
            if m in mention_to_gold:
                gold_counts[tuple(mention_to_gold[m])] += 1
        for c2, count in gold_counts.iteritems():
            if len(c2) != 1:
                correct += count * count

        num += correct / float(len(c))
        dem += len(c)

    return num, dem


def muc(clusters, mention_to_gold):
    tp, p = 0, 0
    for c in clusters:
        p += len(c) - 1
        tp += len(c)
        linked = set()
        for m in c:
            if m in mention_to_gold:
                linked.add(mention_to_gold[m])
            else:
                tp -= 1
        tp -= len(linked)
    return tp, p


def phi4(c1, c2):
    return 2 * len([m for m in c1 if m in c2]) / float(len(c1) + len(c2))


def ceafe(clusters, gold_clusters):
    clusters = [c for c in clusters if len(c) != 1]
    scores = np.zeros((len(gold_clusters), len(clusters)))
    for i in range(len(gold_clusters)):
        for j in range(len(clusters)):
            scores[i, j] = phi4(gold_clusters[i], clusters[j])
    matching = linear_assignment(-scores)
    similarity = sum(scores[matching[:, 0], matching[:, 1]])
    return similarity, len(clusters), similarity, len(gold_clusters)

"""##The main components for our coreference resolution system
Now you are ready to go! Let first create a single class (CorefModel) to store all the elements we needed for our simple coreference system. 

###In the \__init__() method we intialize the network parameters.
Here we hardcoded them. For a real system, usually, the parameters will be stored in a configuration file, as there will be many of them.
"""

import time
import json
import numpy as np
import tensorflow as tf
import collections

class CorefModel(object):
  def __init__(self,embedding_path, embedding_size):
    tf.reset_default_graph()
    self.embedding_path = embedding_path #The path to the pre-trained word embeddings
    self.embedding_size = embedding_size #The dimension of the pretrained embeddings
    self.embedding_dropout_rate = 0.5 #The dropout rate for word embeddings
    self.max_ant = 250 #The maximum number of candidate antecedents we will give to each of the candidate mentions.
    self.hidden_size = 150 #The size of the hidden layer, include both LSTM and feedforward NN
    self.ffnn_layer = 2 #The number of hidden layers used for the feedforward NN
    self.hidden_dropout_rate = 0.2 #The dropout rate for the hidden layers of LSTM and feedforward NN

"""###The build() method builds a tensorflow graph for our task
This method first loads the pre-trained word embeddings from the given location by calling the `load_embeddings` method:
"""

def load_embeddings(self, path, size):
    print("Loading word embeddings from {}...".format(path))
    embeddings = collections.defaultdict(lambda: np.zeros(size))
    firstline=True
    for line in open(path):
      if firstline:
        firstline=False
        continue
      splitter = line.find(' ')
      emb = np.fromstring(line[splitter + 1:], np.float32, sep=' ')
      assert len(emb) == size
      embeddings[line[:splitter]] = emb
    print("Finished loading word embeddings")
    return embeddings
  CorefModel.load_embeddings = load_embeddings

"""It then creates placeholders, which are the inputs of the tensorflow graph."""

def add_placeholder(self):
    self.word_embeddings = tf.placeholder(tf.float32, shape=[None, None,self.embedding_size])
    self.sent_lengths = tf.placeholder(tf.int32, shape=[None])
    self.mention_starts = tf.placeholder(tf.int32, shape=[None])
    self.mention_ends = tf.placeholder(tf.int32, shape=[None])
    self.mention_cluster_ids = tf.placeholder(tf.int32, shape=[None])
    self.is_training = tf.placeholder(tf.bool, shape=[])
  CorefModel.add_placeholder = add_placeholder

"""After that, the method calls the `get_predictions_and_loss` method to create the rest of the tensorflow graph."""

def get_predictions_and_loss(self,word_embeddings,sent_lengths,mention_starts,mention_ends,mention_cluster_ids,is_training):
    #get the keep probability
    embedding_keep_prob = 1 - (tf.to_float(is_training)*self.embedding_dropout_rate)
    hidden_keep_prob = 1 - (tf.to_float(is_training)*self.hidden_dropout_rate)


    #bidirectional LSTM over sentences
    word_embeddings = tf.nn.dropout(word_embeddings,embedding_keep_prob)
    word_lstm_for = tf.nn.rnn_cell.DropoutWrapper(tf.nn.rnn_cell.LSTMCell(self.hidden_size),
                                                  state_keep_prob=hidden_keep_prob,
                                                  variational_recurrent=True,
                                                  dtype=tf.float32)
    word_lstm_rev = tf.nn.rnn_cell.DropoutWrapper(tf.nn.rnn_cell.LSTMCell(self.hidden_size),
                                                  state_keep_prob=hidden_keep_prob,
                                                  variational_recurrent=True,
                                                  dtype=tf.float32)
    (output_for, output_rev), _ = tf.nn.bidirectional_dynamic_rnn(
      word_lstm_for, word_lstm_rev, word_embeddings,
      sequence_length=sent_lengths, dtype=tf.float32
    )


    word_output = tf.concat([output_for, output_rev], axis=-1)
    
    #remove paddings from the word output
    num_sents = shape(word_embeddings, 0)
    max_sent_length = shape(word_embeddings, 1)
    
    word_seq_mask = tf.sequence_mask(sent_lengths, max_sent_length)
    flatten_word_seq_mask = tf.reshape(word_seq_mask, [num_sents * max_sent_length])
    flatten_word_output = tf.reshape(word_output, [num_sents * max_sent_length, 2 * self.hidden_size])
    flatten_word_output = tf.nn.dropout(flatten_word_output, hidden_keep_prob)
    flatten_word_output = tf.boolean_mask(flatten_word_output, flatten_word_seq_mask, axis=0)
    
    #create the mention representation from the word output 
    #by concatenating word_output at the positions of mention’s start and end indices
    mention_starts_emb = tf.gather(flatten_word_output,mention_starts)
    mention_ends_emb = tf.gather(flatten_word_output,mention_ends)
    mention_emb = tf.concat([mention_starts_emb,mention_ends_emb],axis=1)
    
    #In order to do coreference, we also need to create the candidate antecedents.
    #Here we give each of the candidate mentions a maximum 250 candidate antecedents
    #(candidate mentions that before the current mention).
    num_mention = shape(mention_emb, 0)
    max_ant = tf.minimum(num_mention,self.max_ant)
    antecedents = tf.expand_dims(tf.range(num_mention),1) \
                  - tf.tile(tf.expand_dims(tf.range(max_ant)+1, 0), [num_mention, 1])
    antecedents_mask = antecedents >= 0
    antecedents = tf.maximum(antecedents, 0)
    antecedents_emb = tf.gather(mention_emb, antecedents)

    #After that,  we concatenate the mentions embeddings with the antecedent 
    #embeddings to create the mention pair embeddings.
    tiled_mention_emb = tf.tile(tf.expand_dims(mention_emb, 1), [1,max_ant,1])
    mention_pair_emb = tf.concat([tiled_mention_emb, antecedents_emb], 2)
    ffnn_input = tf.reshape(mention_pair_emb,[num_mention*max_ant, 8 * self.hidden_size])


    #create a multilayer feed-forward neural network to compute mention pair scores.
    for i in range(self.ffnn_layer):
      hidden_weights = tf.get_variable("hidden_weights_{}".format(i),[shape(ffnn_input,1), self.hidden_size])
      hidden_bias = tf.get_variable("hidden_bias_{}".format(i), [self.hidden_size])
      ffnn_output = tf.nn.relu(tf.nn.xw_plus_b(ffnn_input, hidden_weights,hidden_bias))
      ffnn_output = tf.nn.dropout(ffnn_output, hidden_keep_prob)
      ffnn_input = ffnn_output

    output_weights = tf.get_variable("output_weights", [shape(ffnn_input, 1), 1])
    output_bias = tf.get_variable("output_bias", [1])
    mention_pair_scores = tf.nn.xw_plus_b(ffnn_input,output_weights,output_bias)

    mention_pair_scores = tf.reshape(mention_pair_scores,[num_mention,max_ant])
    mention_pair_scores += tf.log(tf.to_float(antecedents_mask))

    dummy_scores = tf.zeros([num_mention,1])

    mention_pair_scores = tf.concat([dummy_scores,mention_pair_scores], 1)

    #create the gold label for training
    antecedents_cluster_ids = tf.gather(mention_cluster_ids,antecedents) + tf.to_int32(tf.log(tf.to_float(antecedents_mask)))
    mention_pair_labels = tf.logical_and(
      tf.equal(antecedents_cluster_ids, tf.expand_dims(mention_cluster_ids, 1)),
      tf.greater(antecedents_cluster_ids, 0))
    dummy_labels = tf.logical_not(tf.reduce_any(mention_pair_labels,1,keepdims=True))
    mention_pair_labels = tf.concat([dummy_labels,mention_pair_labels],1)
    
    
    #compute the loss
    gold_scores = mention_pair_scores + tf.log(tf.to_float(mention_pair_labels))
    marginalized_gold_scores = tf.reduce_logsumexp(gold_scores,1)
    log_norm = tf.reduce_logsumexp(mention_pair_scores,1)
    loss = log_norm - marginalized_gold_scores
    loss = tf.reduce_sum(loss)

    return [antecedents, mention_pair_scores], loss
  CorefModel.get_predictions_and_loss = get_predictions_and_loss

"""Finally, the method defines the training mechanism and initializes global variables of our model."""

def build(self):
    #loads pre-trained word embeddings
    self.embedding_dict = self.load_embeddings(self.embedding_path, self.embedding_size)
    
    #create placeholders
    self.add_placeholder()

    #create tensorflow graph
    self.predictions, self.loss = self.get_predictions_and_loss(
      self.word_embeddings,self.sent_lengths,self.mention_starts,self.mention_ends,
      self.mention_cluster_ids,self.is_training)

    #define training mechanism
    trainable_params = tf.trainable_variables()
    gradients = tf.gradients(self.loss, trainable_params)
    gradients, _ = tf.clip_by_global_norm(gradients,5.0)
    optimizer = tf.train.AdamOptimizer()
    self.train_op = optimizer.apply_gradients(zip(gradients,trainable_params))
    self.sess = tf.Session()
    self.sess.run(tf.global_variables_initializer())
  CorefModel.build = build

"""###The get_feed_dict_list() method creates inputs for the tensorflow graph.
This method reads documents from the the json files and return a list of `feed_dict` elements, which are used as the input for the tensorflow graph. The method also returns the gold clusters of each documents which are used for evaluation.

Each of the lines in the json files contains information for a single document. The “doc_key" stores the name of the document; the “sentences” points you to tokenized sentences of the document; the “clusters” element stores the coreference clusters. Each of the clusters contains a number of mentions, each of the mentions has a start and an end indices which link back to the sentences.
"""

def get_feed_dict_list(self,path, is_training):
    feed_dict_list = []
    for line in open(path):
      doc = json.loads(line)
      
      #For each document, the method first assigns each mention 
      #a cluster_id according to the clusters it belongs to:
      clusters = doc['clusters']
      gold_mentions = sorted([tuple(m) for cl in clusters for m in cl])
      gold_mention_map = {m:i for i,m in enumerate(gold_mentions)}
      cluster_ids = np.zeros(len(gold_mentions))
      for cid, cluster in enumerate(clusters):
        for mention in cluster:
          cluster_ids[gold_mention_map[tuple(mention)]] = cid + 1
      
      #It then splits the mentions into two arrays, one representing 
      #the start indices, and the other for the end indices:
      starts, ends = [], []
      if len(gold_mentions) > 0:
        starts, ends = zip(*gold_mentions)
      starts, ends = np.array(starts), np.array(ends)
      
      #After that,  it reads the word embeddings for the sentences in the document
      sentences = doc['sentences']
      sent_lengths = [len(sent) for sent in sentences]
      max_sent_length = max(sent_lengths)
      word_emb = np.zeros([len(sentences),max_sent_length,self.embedding_size])
      for i, sent in enumerate(sentences):
        for j, word in enumerate(sent):
          word_emb[i,j] = self.embedding_dict[word]

      #In the end, it creates the feed_dict:
      fd = {}
      fd[self.word_embeddings] = word_emb
      fd[self.sent_lengths] = np.array(sent_lengths)
      fd[self.mention_starts] = starts
      fd[self.mention_ends] = ends
      fd[self.mention_cluster_ids] = cluster_ids
      fd[self.is_training] = is_training
      feed_dict_list.append(tuple((fd,clusters)))

    return feed_dict_list
  CorefModel.get_feed_dict_list = get_feed_dict_list

"""###The get_predicted_clusters() method creates the predicted clusters from the predicted antecedents
The outputs of the `get_predictions_and_loss()` method is not yet clusters, instead it returns predicted antecedents, so we need to group them as clusters.
"""

def get_predicted_clusters(self, mention_starts, mention_ends, predicted_antecedents):
    mention_to_predicted = {}
    predicted_clusters = []

    for i, predicted_index in enumerate(predicted_antecedents):
      if predicted_index < 0:
        continue
      assert i > predicted_index
      predicted_antecedent = (int(mention_starts[predicted_index]), int(mention_ends[predicted_index]))
      if predicted_antecedent in mention_to_predicted:
        predicted_cluster = mention_to_predicted[predicted_antecedent]
      else:
        predicted_cluster = len(predicted_clusters)
        predicted_clusters.append([predicted_antecedent])
        mention_to_predicted[predicted_antecedent] = predicted_cluster

      mention = (int(mention_starts[i]), int(mention_ends[i]))
      predicted_clusters[predicted_cluster].append(mention)
      mention_to_predicted[mention] = predicted_cluster

    predicted_clusters = [tuple(pc) for pc in predicted_clusters]
    mention_to_predicted = {m: predicted_clusters[i] for m, i in mention_to_predicted.items()}


    return predicted_clusters, mention_to_predicted
  CorefModel.get_predicted_clusters = get_predicted_clusters

"""###The evaluate_coref() method updates the coreference scorer
The method first creates `gold_clusters` and `mention_to_gold` which are required by the coreference scorer. It is important that both clusters and mentions should be tuples in order to be used by the scorer. `mention_to_gold` is the map from mention to clusters. It then creates predicted clusters by calling the `get_predicted_clusters` method. After obtaining both gold and predicted clusters, the method updates the scorer.
"""

def evaluate_coref(self, mention_starts, mention_ends, predicted_antecedents, gold_clusters, evaluator):
    gold_clusters = [tuple(tuple(m) for m in gc) for gc in gold_clusters]
    mention_to_gold = {}
    for gc in gold_clusters:
      for mention in gc:
        mention_to_gold[mention] = gc

    predicted_clusters, mention_to_predicted = \
    self.get_predicted_clusters(mention_starts, mention_ends,
                                  predicted_antecedents)
    evaluator.update(predicted_clusters, gold_clusters, mention_to_predicted, mention_to_gold)
  CorefModel.evaluate_coref = evaluate_coref

"""###The train() method oversees the training process.
It first loads the training data. Then training the model by go through the all the training documents  a number of times. It also outputs the average loss and time usage of the training.After each epoch, the model evaluates on the development set. Normally, the model will be written to the disk if a better dev score is obtained. Here we didn’t do that to simplify the code for lab use. After finished all the training epochs, it evaluates on the final test set.
"""

def train(self, train_path,dev_path,test_path, epochs):
    train_fd_list = self.get_feed_dict_list(train_path, True)
    start_time = time.time()
    for epoch in range(epochs):
      print("Starting training epoch {}/{}".format(epoch+1,epochs))
      epoch_time = time.time()
      losses = []
      for i, (fd, _) in enumerate(train_fd_list):
        _,loss = self.sess.run([self.train_op,self.loss], feed_dict=fd)
        losses.append(loss)
        if i>0 and i%200 == 0:
          print("[{}]: loss:{:.2f}".format(i,sum(losses[i-200:])/200.0))
      print("Average epoch loss:{}".format(sum(losses)/len(losses)))
      print("Time used for epoch {}: {}".format(epoch+1, time_used(epoch_time)))
      dev_time = time.time()
      print("Evaluating on dev set after epoch {}/{}:".format(epoch+1,epochs))
      self.eval(dev_path)
      print("Time used for evaluate on dev set: {}".format(time_used(dev_time)))

    print("Training finished!")
    print("Time used for training: {}".format(time_used(start_time)))

    print("Evaluating on test set:")
    test_time = time.time()
    self.eval(test_path)
    print("Time used for evaluate on test set: {}".format(time_used(test_time)))
  CorefModel.train = train

"""###The eval() method runs a test on the given dataset.
The method  first reads the dataset. Then, it creates an instance of the coreference scorer. After that,  it evaluates the dataset document by document. In the end, it gets the scores from the coreference scorer.
"""

def eval(self, path):
    eval_fd_list = self.get_feed_dict_list(path, False)
    coref_evaluator = CorefEvaluator()

    for fd, clusters in eval_fd_list:
      mention_starts,mention_ends = fd[self.mention_starts],fd[self.mention_ends]
      antecedents, mention_pair_scores = self.sess.run(self.predictions, fd)

      predicted_antecedents = []
      for i, index in enumerate(np.argmax(mention_pair_scores, axis=1) - 1):
        if index < 0:
          predicted_antecedents.append(-1)
        else:
          predicted_antecedents.append(antecedents[i, index])

      self.evaluate_coref(mention_starts,mention_ends,predicted_antecedents,clusters,coref_evaluator)

    p, r, f = coref_evaluator.get_prf()
    print("Average F1 (py): {:.2f}%".format(f * 100))
    print("Average precision (py): {:.2f}%".format(p * 100))
    print("Average recall (py): {:.2f}%".format(r * 100))
  CorefModel.eval = eval

"""### Finally, the \__main__ method starts the training.
It also configures the model by providing the locations of all the files needed for the model.
"""

if __name__ == '__main__':
  embedding_path = 'model.txt'
  train_path = '20MinsNLP-2019-04-02-Coreference-Data/train.english.pd2.0.conll.jsonlines'
  dev_path = '20MinsNLP-2019-04-02-Coreference-Data/dev.english.pd2.0.conll.jsonlines'
  test_path = '20MinsNLP-2019-04-02-Coreference-Data/test.english.pd2.0.conll.jsonlines'
  embedding_size = 300
  model = CorefModel(embedding_path,embedding_size)
  model.build()
  model.train(train_path,dev_path,test_path,5)

"""##Further readings about the state-of-the-art coreference systems
["End-to-end Neural Coreference Resolution"](http://kentonl.com/pub/lhlz-emnlp.2017.pdf).
Kenton Lee, Luheng He, Mike Lewis, Luke Zettlemoyer.
EMNLP 2017.

["Higher-order Coreference Resolution with Coarse-to-fine Inference"](https://arxiv.org/abs/1804.05392). 
Kenton Lee, Luheng He, Luke Zettlemoyer.
NAACL 2018.

["Deep Reinforcement Learning for Mention-Ranking Coreference Models"](http://cs.stanford.edu/people/kevclark/resources/clark-manning-emnlp2016-deep.pdf). Kevin Clark and Christopher D. Manning. EMNLP 2016.

["Improving Coreference Resolution by Learning Entity-Level Distributed Representations"](http://cs.stanford.edu/people/kevclark/resources/clark-manning-acl16-improving.pdf). Kevin Clark and Christopher D. Manning. ACL 2016.
"""