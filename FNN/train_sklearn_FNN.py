from __future__ import print_function
from time import time
import numpy as np
import sys, os, operator, pickle
import matplotlib.pyplot as plt
from sklearn.decomposition import RandomizedPCA
from sklearn.metrics import precision_recall_curve
from sklearn.metrics import average_precision_score
from pybrain.structure import TanhLayer
from pybrain.datasets import ClassificationDataSet
from pybrain.utilities import percentError
from pybrain.tools.shortcuts import buildNetwork
from pybrain.supervised.trainers import BackpropTrainer
from pybrain.structure.modules import SoftmaxLayer

### Global variables
display_graphs = False # Boolean flag for displaying graphs
vocabulary = {} # A dictionary of all the unique words in the corpus

### Change me to higher values for better accuracy!
NUM_FEATURES = 2000 # The number of most common words in the corpus to use as features
PERCENTAGE_DATA_SET_TO_USE = 0.05 # The percentage of the dataset to use
N_COMPONENTS = 200 # The number of components for the PCA
N_HIDDEN = 32
N_EPOCHS = 7
trainer = None
classifier = None

###############################################################################

def load_parsed_data():
    """
    Loads the train, test, and validation sets

    Returns:
        inputs_train   the input train set
        targets_train  the target train set
        inputs_valid   the input validation set
        targets_valid  the target validation set
        inputs_test    the input test set
        targets_test   the target test set
    """
    print('loading parsed dataset')
    inputs_train  = np.load('../parsed_data/inputs_train.npy')
    targets_train = np.load('../parsed_data/targets_train.npy')
    inputs_valid  = np.load('../parsed_data/inputs_valid.npy')
    targets_valid = np.load('../parsed_data/targets_valid.npy')
    inputs_test   = np.load('../parsed_data/inputs_test.npy')
    targets_test  = np.load('../parsed_data/targets_test.npy')
    print('loaded parsed dataset')


    return inputs_train, targets_train, inputs_valid, targets_valid, inputs_test, targets_test

def trained_model_exists():
    """
    Checks to see if the extracted features for the Naive Bayes
    models are saved.

    Returns:
        boolean  True iff file 'data/model.pkl' exists
    """
    return os.path.exists('data/model.pkl')

def load_trained_model():
    """Loads and returns the trained model"""
    print('loading trained model')
    with open('data/model.pkl', 'rb') as input:
        classifier = pickle.load(input)
        print('loaded trained model')
        input.close()
    return classifier

def load_pca():
    with open('data/pca.pkl', 'rb') as input:
        pca = pickle.load(input)
        print('loaded pca')
        input.close()
    return pca

def save_model(classifier):
    """Saves the model"""
    print('saving trained model')
    with open('data/model.pkl', 'wb') as output:
        pickle.dump(classifier, output, pickle.HIGHEST_PROTOCOL)
        print('saved trained model')

def save_pca(pca):
    with open('data/pca.pkl', 'wb') as output:
        pickle.dump(pca, output, pickle.HIGHEST_PROTOCOL)
        print('saved pca')

def load_features():
    """
    Loads the extracted features for each data set

    Returns:
        train_features  a dictionary of the features in the train set
        valid_features  a dictionary of the features in the validation set
        test_features   a dictionary of the features in the test set
    """
    print('loading extracted features')
    train_features = np.load('data/train_features.npy')
    valid_features = np.load('data/valid_features.npy')
    test_features  = np.load('data/test_features.npy')
    print('loaded extracted features')
    return train_features, valid_features, test_features

def save_features(train_features, valid_features, test_features):
    """Saves the extracted features for each dataset"""
    print('saving extracted features')
    np.save('data/train_features.npy', train_features)
    np.save('data/valid_features.npy', valid_features)
    np.save('data/test_features.npy', test_features)
    print('saved extracted features')

def build_vocabulary(inputs):
    """
    Builds a dictionary of unique words in the corpus

    Returns:
        vocabulary  a dictionary of all the unique words in the corpus
    """
    print('building vocabulary of words in the corpus')
    global vocabulary

    for tweet in inputs:
        for word in str(tweet).split():
            if vocabulary.has_key(word):
                vocabulary[word] += 1
            else:
                vocabulary[word] = 1

    print('built vocabulary of words in the corpus')
    return vocabulary

def build_features(document, i, vocabulary_words):
    if i % 10000 == 0:
        print('extracted features for {0} tweets'.format(i))

    document_words = set(str(document).split())
    features = np.zeros(len(vocabulary_words))
    for i in range(len(vocabulary_words)):
        features[i] = (vocabulary_words[i] in document_words)
    return features

def extract_features(inputs_train, targets_train, inputs_valid, targets_valid, inputs_test, targets_test):
    """
    Extracts features for training the model.

    Returns:
        train_features   a dictionary of word presence in the entire input
                         dataset for each tweet
                         {'contains(lol)': False, 'contains(jbiebs)': True, ...}

        valid_features   a dictionary of word presence in the entire input
                         dataset for each tweet
                         {'contains(lol)': False, 'contains(jbiebs)': True, ...}

        test_features    a dictionary of word presence in the entire input
                         dataset for each tweet
                         {'contains(lol)': False, 'contains(jbiebs)': True, ...}
    """
    inputs = np.hstack((inputs_train, inputs_valid, inputs_test))
    vocabulary = build_vocabulary(inputs)

    # Get most common words from vocabulary
    global NUM_FEATURES
    words = dict(sorted(vocabulary.iteritems(), key=operator.itemgetter(1), reverse=True)[:NUM_FEATURES])
    words = words.keys()

    print('extracting features for all tweets')
    train_features = [(build_features(inputs_train[i], i, words)) for i in range(len(inputs_train))]
    valid_features = [(build_features(inputs_valid[i], i, words)) for i in range(len(inputs_valid))]
    test_features  = [(build_features(inputs_test[i], i, words)) for i in range(len(inputs_test))]
    print('extracted features for all tweets')

    return np.array(train_features), np.array(valid_features), np.array(test_features)

def plot_precision_and_recall(predictions, targets):
    """Calculates and displays the precision and recall graph"""

    # Compute Precision-Recall and plot curve
    precision = dict()
    recall = dict()
    average_precision = dict()
    average_precision = average_precision_score(targets, predictions)
    precision, recall, _ = precision_recall_curve(targets, predictions)

    # Plot Precision-Recall curve
    plt.clf()
    plt.plot(recall, precision, label='Precision-Recall curve')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall example: AUC={0:0.2f}'.format(average_precision))
    plt.legend(loc="lower left")
    plt.show()

def make_prediction(tstdata):
    global trainer
    if trainer is not None:
        error = percentError(trainer.testOnClassData(
                        dataset=tstdata)
                        , tstdata['class'])
        print ('Percent Error on dataset: ', error)

def train_model( trndata, valid_data ):
    print("Fitting the classifier to the training set")
    t0 = time()
    for i in range(1, N_EPOCHS+1):
            trainer.trainEpochs(1)
            make_prediction(valid_data)
    print("done in %0.3fs" % (time() - t0))
    return

def main():
    """
    CLI Arguments allowed:
        --display_graphs       Displays graphs
        --retrain              Trains a new model
        --cross-validate       Runs cross validation to fine tune the model
        --test=validation_set  Tests the latest trained model against the validation set
        --test=test_set        Tests the latets trained model against the test set
    """

    global trainer, classifier
    inputs_train, targets_train, inputs_valid, targets_valid, inputs_test, targets_test = load_parsed_data()

    if '--display_graphs' in sys.argv:
        display_graphs = True

    print('using {} percent of all data in corpus'.format(PERCENTAGE_DATA_SET_TO_USE*100))
    print('using {} most common words as features'.format(NUM_FEATURES))

    if not trained_model_exists() or '--retrain' in sys.argv:
        train_features, valid_features, test_features = extract_features(
            inputs_train[:len(inputs_train)*PERCENTAGE_DATA_SET_TO_USE],
            targets_train[:len(targets_train)*PERCENTAGE_DATA_SET_TO_USE],
            inputs_valid[:len(inputs_valid)*PERCENTAGE_DATA_SET_TO_USE],
            targets_valid[:len(targets_valid)*PERCENTAGE_DATA_SET_TO_USE],
            inputs_test[:len(inputs_test)*PERCENTAGE_DATA_SET_TO_USE],
            targets_test[:len(targets_test)*PERCENTAGE_DATA_SET_TO_USE]
        )

        save_features(train_features, valid_features, test_features)
        pca = RandomizedPCA(n_components=N_COMPONENTS, whiten=False).fit(train_features)
        save_pca(pca)
        print ("Saved PCA")

        X_train = pca.transform(train_features)
        X_valid = pca.transform(valid_features)
        pca = None
        print ("Created PCAd features")

        valid_data = ClassificationDataSet(N_COMPONENTS, target=1, nb_classes=2)
        for i in range(len(X_valid)):
            valid_data.addSample(X_valid[i], targets_test[i])
        valid_data._convertToOneOfMany()
        X_valid = None

        train_data = ClassificationDataSet(N_COMPONENTS, target=1, nb_classes=2)
        for i in range(len(X_train)):
            train_data.addSample( X_train[i], targets_train[i])
        train_data._convertToOneOfMany()
        X_train = None

        classifier = buildNetwork( train_data.indim, N_HIDDEN, train_data.outdim, outclass=SoftmaxLayer)
        trainer = BackpropTrainer( classifier, dataset=train_data, momentum=0.1, learningrate=0.01 , verbose=True)
        train_model(train_data, valid_data)

        save_model(classifier)
        train_data = None
        valid_data = None

    else:
        train_features, valid_features, test_features = load_features()
        pca = load_pca()
        X_train = pca.transform(train_features)

        pca = None
        print ("Created PCAd features")

        train_data = ClassificationDataSet(N_COMPONENTS, target=1, nb_classes=2)
        for i in range(len(X_train)):
            train_data.addSample( X_train[i], targets_train[i])
        train_data._convertToOneOfMany()
        X_train = None

        classifier = load_trained_model()
        trainer = BackpropTrainer( classifier, dataset=train_data, momentum=0.1, learningrate=0.01 , verbose=True)


    if '--test=validation_set' in sys.argv:
        print ("Running against validation set")
        pca = load_pca()
        X_valid = pca.transform(valid_features)
        pca = None
        valid_data = ClassificationDataSet(N_COMPONENTS, target=1, nb_classes=2)
        for i in range(len(X_valid)):
            valid_data.addSample( X_valid[i], targets_test[i])
        valid_data._convertToOneOfMany()
        X_valid = None

        make_prediction(valid_data)


    if '--test=test_set' in sys.argv:
        print ("Running against test set")
        pca = load_pca()
        X_test = pca.transform(test_features)
        pca = None
        test_data = ClassificationDataSet(N_COMPONENTS, target=1, nb_classes=2)
        for i in range(len(X_test)):
            test_data.addSample( X_test[i], targets_test[i])
        test_data._convertToOneOfMany()
        y_pred = trainer.testOnClassData(dataset=test_data)
        plot_precision_and_recall(y_pred, targets_test[:len(targets_test) * PERCENTAGE_DATA_SET_TO_USE])
        X_test = None

        make_prediction(test_data)

if __name__ == "__main__": main()
