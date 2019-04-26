import numpy as np
import sys, os
import pandas as pd
import matplotlib.pyplot as plot
from transform_features import transform_features
from classification_strategies import ClassificationStrategy, PerFrameClassification, simpleBufferClassification
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.naive_bayes import GaussianNB
from constants import PERSONS, ACTIONS

devnull = open(os.devnull, 'w')

names = ["Nearest Neighbors", "RBF SVM", "Random Forest", "AdaBoost",
         "Naive Bayes"]
# mogelijkheden: per actie een andere classifier trainen
classifiers = [
    KNeighborsClassifier(3),
    SVC(gamma='scale', C=100),
    RandomForestClassifier(max_depth=5, n_estimators=10, max_features=1),
    AdaBoostClassifier(),
    GaussianNB(),
]


class Dataset(object):
    """
    This class represents a dataset that is compatible with the sklearn machine learning library
    """
    def __init__(self):
        self.data = []
        self.target = []
    
    def __len__(self):
        return len(self.data) # data and target attribute always have same length

def loadTrainingset(trainingPersons):
    trainingset = Dataset() # trainingset is a n * k matrix with n = # samples (frames) and k = # features (175)
    for person in trainingPersons:
        for action in ACTIONS:
            folder = f"data\\{person}\\{action}"
            try:
                joints = pd.read_csv(f"{folder}\\joints.txt", header = None, sep = ';')
                labels = pd.read_csv(f"{folder}\\labels.txt", header = None)
                trainingset.target.extend(labels.to_numpy().ravel())
                trainingset.data.extend(transform_features(f"{folder}\\joints.txt"))
            except FileNotFoundError as fnfe:
                devnull.write(str(fnfe))
    return trainingset

def loadValidationset(validationPerson):
    validationset = Dataset() 
    for action in ACTIONS:
        folder = f"data\\{validationPerson}\\{action}"
        try:
            joints = pd.read_csv(f"{folder}\\joints.txt", header = None, sep = ';')
            labels = pd.read_csv(f"{folder}\\labels.txt", header = None)
            validationset.target.extend(labels.to_numpy().ravel())
            validationset.data.extend(transform_features(f"{folder}\\joints.txt"))
        except FileNotFoundError as fnfe:
            devnull.write(str(fnfe))
    return validationset

avgPrecisions = [0] * len(classifiers)
avgRecalls = [0] * len(classifiers)
avgF1scores = [0] * len(classifiers)

for i in range(1, len(PERSONS) + 1):
    testPersons = PERSONS[:i - 1] + PERSONS[i:]
    validationPerson = PERSONS[i - 1]
    trainingset = loadTrainingset(testPersons)
    validationset = loadValidationset(validationPerson)
    listPrecisions = [] # used to make a graph 
    listRecalls = []
    listF1scores = []
    for clf in classifiers:
        strategy = PerFrameClassification(trainingset, validationset, clf)
        strategy.perform()
        listPrecisions.append(strategy.calculatePrecision())
        listRecalls.append(strategy.calculateRecall())
        listF1scores.append(strategy.calculateF1Score())

    i = 0
    for p, a, f in zip(listPrecisions, listRecalls, listF1scores):
        avgPrecisions[i] += p
        avgRecalls[i] += a
        avgF1scores[i] += f
        i += 1
    

print(avgPrecisions)
avgPrecisions = [x / len(classifiers) for x in avgPrecisions]
avgRecalls = [x / len(classifiers) for x in avgRecalls]
avgF1scores = [x / len(classifiers) for x in avgF1scores]

plot.title("Average precision/recall for each classifier")
plot.plot(avgPrecisions, label = 'precision', linestyle = (0, (1, 10)), marker='o')
plot.plot(avgRecalls, label = 'recall', linestyle = (0, (1, 10)), marker='o')
plot.plot(avgF1scores, label = 'F1 score', linestyle = (0, (1, 10)), marker='o')
plot.legend()
plot.xticks(np.arange(5), names)
plot.xlabel('classifier')
plot.ylabel('percentage')
axes = plot.gca()
axes.set_ylim([0, 100])
plot.show()