#!/usr/bin/env python3
# -*- coding: utf-8
#
# Gibran Fuentes-Pineda <gibranfp@unam.mx>
# IIMAS, UNAM
# 2019
#
"""
Script to evaluate the EEGNet architecture (Lawhern et al., 2018) for single-trial subject-dependent P300 detection 
"""
import argparse
import sys
import numpy as np
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import to_categorical
from tensorflow import set_random_seed
from sklearn.model_selection import *
from EEGModels import EEGNet
from utils import *
import tensorflow.keras.backend as K

def evaluate_subject_models(data, labels, modelpath, subject):
    """
    Trains and evaluates EEgNet for a given subject in the P300 Speller database
    using repeated stratified K-fold cross validation.
    """
    n_sub = data.shape[0]
    n_ex_sub = data.shape[1]
    n_samples = data.shape[2]
    n_channels = data.shape[3]
    aucs = np.zeros(5 * 10)
    print("Training for subject {0}: ".format(subject))
    cv = RepeatedStratifiedKFold(n_splits = 5, n_repeats = 10, random_state = 123)
    for k, (t, v) in enumerate(cv.split(data[subject], labels[subject])):
        X_train, y_train, X_test, y_test = data[subject, t, :, :], labels[subject, t], data[subject, v, :, :], labels[subject, v]
        X_train, X_valid, y_train, y_valid = train_test_split(X_train, y_train, test_size = 0.2, shuffle = True, random_state = 456)
        print('Partition {0}: X_train = {1}, X_valid = {2}, X_test = {3}'.format(k, X_train.shape, X_valid.shape, X_test.shape))
        
        # channel-wise feature standarization
        sc = EEGChannelScaler(n_channels = n_channels)
        X_train = np.swapaxes(sc.fit_transform(X_train)[:, np.newaxis, :], 2, 3)
        X_valid = np.swapaxes(sc.transform(X_valid)[:, np.newaxis, :], 2, 3)
        X_test = np.swapaxes(sc.transform(X_test)[:, np.newaxis, :], 2, 3)

        model = EEGNet(2, Chans = n_channels, Samples = n_samples)
        print(model.summary())
        model.compile(optimizer = 'adam', loss = 'categorical_crossentropy')

        # Early stopping setting also follows EEGNet (Lawhern et al., 2018)
        es = EarlyStopping(monitor = 'val_loss', mode = 'min', patience = 50, restore_best_weights = True)
        history = model.fit(X_train,
                            to_categorical(y_train),
                            batch_size = 256,
                            epochs = 200,
                            validation_data = (X_valid, to_categorical(y_valid)),
                            callbacks = [es])

        proba_test = model.predict(X_test)
        aucs[k] = roc_auc_score(y_test, proba_test[:, 1])
        print('S{0}, P{1} -- AUC: {2}'.format(subject, k, aucs[k]))
        K.clear_session()
        
    np.savetxt(modelpath + '/s' + str(subject) + '_aucs.npy', aucs)

def main():
    """
    Main function
    """
    try:
        parser = argparse.ArgumentParser()
        parser = argparse.ArgumentParser(
            description="Evaluates single-trial subject-dependent P300 detection using cross-validation")
        parser.add_argument("datapath", type=str,
                            help="Path for the data of the P300 Speller Database (NumPy file)")
        parser.add_argument("labelspath", type=str,
                            help="Path for the labels of the P300 Speller Database (NumPy file)")
        parser.add_argument("modelpath", type=str,
                            help="Path of the directory where the models are to be saved")
        parser.add_argument("--subject", type=int,
                            help="Subject to evaluate")
        args = parser.parse_args()

        np.random.seed(1)
        set_random_seed(2)
        
        data, labels = load_db(args.datapath, args.labelspath)
        evaluate_subject_models(data, labels, args.modelpath, args.subject)
        
    except SystemExit:
        print('for help use --help')
        sys.exit(2)
        
if __name__ == "__main__":
    main()
