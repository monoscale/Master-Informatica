from constants import ACTIONS

class ClassificationStrategy(object):
    """
    A classification strategy implements a classification method. This strategy is independent of the chosen features.
    To evaluate the classifier, it's precision, recall and F1score are calculated. First, a list of precisions and recalls
    are generated from the confusion matrix for each action. The average precision, recall and f1score is then calculated for 
    the global performance of the classifier.
    """
    def __init__(self):
        self.confusionMatrix = [] # The confusion matrix is represented by list in this order: [TP, FP, FN, TN]
        self.recalls = []
        self.precisions = []
        
    
    def __str__(self):
        raise NotImplementedError("This is an abstract method. Implement this in a subclass")

    def calculateRecall(self):  # given a positive example, how likely will the classifier correctly detect it?
        return sum(self.recalls) / len(self.recalls)
    
    def calculatePrecision(self):# given a positive prediction from the classifier: how likely is it to be correct?
        return sum(self.precisions) / len(self.precisions)

    def calculateF1Score(self): # harmonic mean of precision and recall
        f1score = 0
        for precision, recall in zip(self.precisions, self.recalls):
            try:
                f1score += (2 * (precision*recall) / (precision+recall))
            except ZeroDivisionError:
                pass
        return f1score / len(self.precisions)

    def getStatistics(self):
        """
        Returns a tuple containing the values of the calculateRecall, calculatePrecision and calculateF1Score methods.
        """
        return (self.calculateRecall(), self.calculatePrecision(), self.calculateF1Score())

    def perform(self, validationset, classifier):
        raise NotImplementedError("This is an abstract method, implement this in a subclass.")




class PerFrameClassification(ClassificationStrategy):
    """
    This is the simplest method as it classifies each frame individually.
    """ 

    def __init__(self):
        ClassificationStrategy.__init__(self)

    def __str__(self):
        return "PerFrameClassification"


    def perform(self, validationset, classifier):
        predictions = classifier.predict(validationset.data)
     
        for i in range(0, len(ACTIONS)):
            self.confusionMatrix = [0] * 4
            for j in range(0, len(predictions)):
                if(validationset.target[j] == i):
                    if(predictions[j] == i):
                        self.confusionMatrix[0] += 1
                    else:
                        self.confusionMatrix[2] += 1
                elif(validationset.target[j] != i):
                    if(predictions[j] == i):
                        self.confusionMatrix[1] += 1
                    else:
                        self.confusionMatrix[3] += 1
            try:
                (TP, FP, FN) = (self.confusionMatrix[0], self.confusionMatrix[1], self.confusionMatrix[3])
                self.precisions.append(round(TP/(TP + FP), 4) * 100)
                self.recalls.append(round(TP/(TP + FN), 4) * 100)   
            except ZeroDivisionError:
                pass

class SimpleBufferClassification(ClassificationStrategy):
    """
    This classification strategy forms groups of 30 frames in a buffer. The majority action gets calculated incrementally for each frame in this buffer.

    """
    def __init__(self):
        ClassificationStrategy.__init__(self)
        self.bufferSize = 30

    def __str__(self):
        return "SimpleBufferClassification"

    def perform(self, validationset, classifier):
        iterations = (len(validationset) // self.bufferSize)
        for i in range(0, len(ACTIONS)):
            self.confusionMatrix = [0] * 4
            for currentIteration in range(0, iterations):
                bufferTarget = [validationset.target[j] for j in range(currentIteration*self.bufferSize, (currentIteration+1)*self.bufferSize)]
                bufferData =  [validationset.data[j] for j in range(currentIteration*self.bufferSize, (currentIteration+1)*self.bufferSize)]
                predictions = classifier.predict(bufferData)  # let classifier classify the individual frames first
                vote = self._getMajorityVote(predictions)
                for j in range(0, len(bufferTarget)):
                    if(bufferTarget[j] == vote):
                        if(predictions[j] == vote):
                            self.confusionMatrix[0] += 1
                        else:
                            self.confusionMatrix[2] += 1
                    elif(bufferTarget[j] != vote):
                        if(predictions[j] == vote):
                            self.confusionMatrix[1] += 1
                        else:
                            self.confusionMatrix[3] += 1
            try:
                (TP, FP, FN) = (self.confusionMatrix[0], self.confusionMatrix[1], self.confusionMatrix[3])
                self.precisions.append(round(TP/(TP + FP), 4) * 100)
                self.recalls.append(round(TP/(TP + FN), 4) * 100)   
            except ZeroDivisionError:
                pass


    def _getMajorityVote(self, predictions):
        frequency = dict(zip([i for i in range(len(ACTIONS))], [0 for i in range(len(ACTIONS))]))
        for prediction in predictions:
            frequency[max(0, prediction)] += 1 # sometimes the classifier returns 'unknown', or '-1' In that case we map those to 0.
        (maxKey, maxVal) = (-1, -1) #
        for (key, val) in iter(frequency.items()):
            if(val > maxVal):
                maxVal = val
                maxKey = key
        return maxKey

class WeightedBufferClassification(ClassificationStrategy):
    def __init__(self):
        ClassificationStrategy.__init__(self)
        self.bufferSize = 30

    def __str__(self):
        return "WeightedBufferClassification"


    def perform(self, validationset, classifier):
        iterations = (len(validationset) // self.bufferSize)
        for i in range(0, len(ACTIONS)):
            self.confusionMatrix = [0] * 4
            for currentIteration in range(0, iterations):
                bufferTarget = [validationset.target[j] for j in range(currentIteration*self.bufferSize, (currentIteration+1)*self.bufferSize)]
                bufferData =  [validationset.data[j] for j in range(currentIteration*self.bufferSize, (currentIteration+1)*self.bufferSize)]
                predictions = classifier.predict(bufferData)  # let classifier classify the individual frames first
                vote = self._getWeightedVote(predictions)
                for j in range(0, len(bufferTarget)):
                    if(bufferTarget[j] == vote):
                        if(predictions[j] == vote):
                            self.confusionMatrix[0] += 1
                        else:
                            self.confusionMatrix[2] += 1
                    elif(bufferTarget[j] != vote):
                        if(predictions[j] == vote):
                            self.confusionMatrix[1] += 1
                        else:
                            self.confusionMatrix[3] += 1
            try:
                (TP, FP, FN) = (self.confusionMatrix[0], self.confusionMatrix[1], self.confusionMatrix[3])
                self.precisions.append(round(TP/(TP + FP), 4) * 100)
                self.recalls.append(round(TP/(TP + FN), 4) * 100)   
            except ZeroDivisionError:
                pass


    def _getWeightedVote(self, predictions):
        frequency = dict(zip([i for i in range(len(ACTIONS))], [0 for i in range(len(ACTIONS))]))
        for i in range(0, len(predictions)):
            frequency[max(0, predictions[i])] += 1 + i/2

        (maxKey, maxVal) = (-1, -1) #
        for (key, val) in iter(frequency.items()):
            if(val > maxVal):
                maxVal = val
                maxKey = key
        return maxKey   
