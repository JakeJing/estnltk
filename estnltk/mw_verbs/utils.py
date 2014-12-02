# -*- coding: utf-8 -*-
#
#     Various utilities that provide support for:
#      *) indexing words (adding wordIDs, clauseIDs);
#      *) processing/filtering morphologically annotated text tokens;
#

from __future__ import unicode_literals
import re

# ================================================================
#    Indexing word tokens: add 'wordID' to each word 
#    (unique within the sentence)
# ================================================================
def addWordIDs(jsonSent):
    for i in range(len(jsonSent)):
        if 'wordID' in jsonSent[i]:
            assert jsonSent[i]['wordID'] == i, ' Unexpected existing wordID: '+str(jsonSent[i]['wordID'])
        jsonSent[i]['wordID'] = i
    return jsonSent

def removeWordIDs(jsonSent):
    for i in range(len(jsonSent)):
        del jsonSent[i]['wordID']
    return jsonSent

def getWordIDrange(a, b, jsonSent):
    tokens = []
    for i in range(len(jsonSent)):
        assert 'wordID' in jsonSent[i], "Missing wordID in "+str(jsonSent[i])
        if a <= jsonSent[i]['wordID'] and jsonSent[i]['wordID'] < b:
            tokens.append( jsonSent[i] )
    return tokens


# ================================================================
#    Separating sentence into clauses: for each clause,
#    return a group of words belonging to that clause
# ================================================================
def getClausesByClauseIDs(jsonSent):
    clauses   = dict()
    for tokenStruct in jsonSent:
        assert 'clauseID' in tokenStruct, ' clauseID not found in: '+str(tokenStruct)
    clauseIDs = [tokenStruct["clauseID"] for tokenStruct in jsonSent]
    for i in range(len(jsonSent)):
        tokenJson = jsonSent[i]
        clauseId  = tokenJson["clauseID"]
        if clauseId not in clauses:
            clauses[clauseId] = []
        clauses[clauseId].append( tokenJson )
    return clauses


# ================================================================
#   A Template for filtering word tokens based on textual and 
#   morphological constraints;
# ================================================================
class WordTemplate:
    ''' A template for filtering word tokens based on morphological and other constraints.
        WordTemplate can be used, for example, to extract words that have a special 
        part-of-speech (e.g verb, noun), or a special morphological case (e.g. inessive, 
        allative).
        
        It is required that the input word token has been morphologically analysed by 
        pyvabamorf, and is in corresponding JSON-style data structure, which contains 
        morphological analyses of the word and its surface textual information:
            {'analysis': [{'clitic': ...,
                           'ending': ...,
                           'form':   ...,
                           'lemma':  ...,
                           'partofspeech': ...,
                           'root': ...,
                           'root_tokens': ... },
                           ... ],
             'text': ... 
            }
        
        Constraints are defined as regular expressions which are used to check whether 
        the string value of the key (e.g. value of "root", "partofspeech") matches the 
        regular expression. 
        
    '''
    analysisRules  = None
    analysisFields = ["root", "partofspeech", "ending", "form", "clitic", "lemma"]
    otherRules     = None
    def __init__(self, newRules):
        '''A template for filtering word tokens based on morphological and other constraints.
        
           Parameters
           ----------
           newRules: dict of str
                Pairs consisting of an analysis keyword (e.g. 'partofspeech', 'root', 'text' 
                etc) and a regular expression describing required value of that keyword.
        '''
        assert isinstance(newRules, dict), "newRules should be dict!"
        for ruleKey in newRules:
            self.addRule(ruleKey, newRules[ruleKey])

    def addRule(self, field, regExpPattern):
        '''Adds new rule for checking whether a value of the field matches given regular 
           expression regExpPattern;
        
           Parameters
           ----------
           field: str
                keyword, e.g. 'partofspeech', 'root', 'text' etc
           regExpPattern: str
                a regular expression that the value of the field must match (using method 
                re.match( regExpPattern, token[field]) ).
        '''
        compiled = re.compile( regExpPattern )
        if field in self.analysisFields:
            if self.analysisRules == None:
                self.analysisRules = dict()
            self.analysisRules[field] = compiled
        else:
            if self.otherRules == None:
                self.otherRules = dict()
            self.otherRules[field] = compiled

    # =============================================
    #    Matching a single token
    # =============================================
    
    def matches(self, tokenJson):
        '''Determines whether given token (tokenJson) satisfies all the rules listed 
           in the WordTemplate. If the rules describe tokenJson["analysis"], it is 
           required that at least one item in the list tokenJson["analysis"] satisfies 
           all the rules (but it is not required that all the items should satisfy). 
           Returns a boolean value.
        
           Parameters
           ----------
           tokenJson: pyvabamorf's analysis of a single word token;
        '''
        if self.otherRules != None:
            otherMatches = []
            for field in self.otherRules:
                match = field in tokenJson and ((self.otherRules[field]).match(tokenJson[field]) != None)
                otherMatches.append( match )
            if not otherMatches or not all(otherMatches):
                return False
            elif self.analysisRules == None and all(otherMatches):
                return True
        if self.analysisRules != None:
            assert "analysis" in tokenJson, "No 'analysis' found within token: "+str(tokenJson)
            totalMatches = []
            for analysis in tokenJson["analysis"]:
                # Check whether this analysis satisfies all the rules 
                # (if not, discard the analysis)
                matches = []
                for field in self.analysisRules:
                    value = analysis[field] if field in analysis else ""
                    match = (self.analysisRules[field]).match(value) != None
                    matches.append( match )
                    if not match:
                        break
                totalMatches.append( all(matches) )
            #  Return True iff there was at least one analysis that 
            # satisfied all the rules;
            return any(totalMatches)
        return False

    def matchingAnalyses(self, tokenJson):
        '''Determines whether given token (tokenJson) satisfies all the rules listed 
           in the WordTemplate and returns a list of analyses (elements of 
           tokenJson["analysis"]) that are matching all the rules. An empty list is 
           returned if none of the analyses match (all the rules), or (!) if none of 
           the rules are describing the "analysis" part of the token;
        
           Parameters
           ----------
           tokenJson: pyvabamorf's analysis of a single word token;
        '''
        matchingResults = []
        if self.otherRules != None:
            otherMatches = []
            for field in self.otherRules:
                match = field in tokenJson and ((self.otherRules[field]).match(tokenJson[field]) != None)
                otherMatches.append( match )
            if not otherMatches or not all(otherMatches):
                return matchingResults
        if self.analysisRules != None:
            assert "analysis" in tokenJson, "No 'analysis' found within token: "+str(tokenJson)
            for analysis in tokenJson["analysis"]:
                # Check whether this analysis satisfies all the rules 
                # (if not, discard the analysis)
                matches = []
                for field in self.analysisRules:
                    value = analysis[field] if field in analysis else ""
                    match = (self.analysisRules[field]).match(value) != None
                    matches.append( match )
                if matches and all(matches):
                    matchingResults.append( analysis )
            #  Return True iff there was at least one analysis that 
            # satisfied all the rules;
            return matchingResults
        return matchingResults

    def matchingAnalyseIndexes(self, tokenJson):
        '''Determines whether given token (tokenJson) satisfies all the rules listed 
           in the WordTemplate and returns a list of analyse indexes that correspond 
           to tokenJson["analysis"] elements that are matching all the rules. 
           An empty list is returned if none of the analyses match (all the rules), 
           or (!) if none of the rules are describing the "analysis" part of the 
           token;

           Parameters
           ----------
           tokenJson: pyvabamorf's analysis of a single word token;
        '''
        matchingResults = self.matchingAnalyses(tokenJson)
        if matchingResults:
            indexes = [ tokenJson["analysis"].index(analysis) for analysis in matchingResults ]
            return indexes
        return matchingResults

    # =============================================
    #    Matches from a list of tokens
    # =============================================

    def matchingPositions(self, tokenArray):
        '''Returns a list of positions (indexes) in the tokenArray where this WordTemplate
           matches (the method self.matches(token) returns True). Returns an empty list if
           no matching tokens appear in the input list.

           Parameters
           ----------
           tokenArray: list of word tokens;
                A list of word tokens along with their pyvabamorf's analyses;
        '''
        assert isinstance(tokenArray, list), "tokenArray should be list "+str(tokenArray)
        matchingPos = []
        for i in range( len(tokenArray) ):
            token = tokenArray[i]
            if self.matches(token):
                matchingPos.append( i )
        return matchingPos

    def matchingTokens(self, tokenArray):
        '''Returns a list of tokens in the tokenArray that match this WordTemplate (the 
           method self.matches(token) returns True). Returns an empty list if no matching 
           tokens appear in the input list.

           Parameters
           ----------
           tokenArray: list of word tokens;
                A list of word tokens along with their pyvabamorf's analyses;
        '''
        assert isinstance(tokenArray, list), "tokenArray should be list "+str(tokenArray)
        matchingTok = []
        for i in range( len(tokenArray) ):
            token = tokenArray[i]
            if self.matches(token):
                matchingTok.append( token )
        return matchingTok
