import stanza
import streamlit as st

puncList = ['.', ',', ':', ';', '!', '?', '\'', '\"', '，', '。', '：', '；', '！', '？']
languageWithBlankSpace = ['en']

def mergeCurrentNodeAndRoot(currentNode:int, rootNode:int, direction:int, dependentTree:list, theNumberOfChildrenInDependentTree:list, theNumberOfWords:int)->int:
	if dependentTree[rootNode][currentNode] == 1 and theNumberOfChildrenInDependentTree[currentNode] == 0:
		return 1
	if currentNode + direction in range(0, theNumberOfWords + 1)\
		and currentNode + direction * 2 in range(0, theNumberOfWords + 1)\
		and dependentTree[rootNode][currentNode] == 1\
		and dependentTree[currentNode][currentNode + direction] == 1\
		and theNumberOfChildrenInDependentTree[currentNode] == 1\
		and theNumberOfChildrenInDependentTree[currentNode + direction] == 0\
		and dependentTree[rootNode][currentNode + direction * 2] == 1\
		and theNumberOfChildrenInDependentTree[currentNode + direction * 2] == 0:
		return 2
	if currentNode + direction in range(0, theNumberOfWords + 1)\
		and dependentTree[rootNode][currentNode + direction] == 1\
		and dependentTree[currentNode + direction][currentNode] == 1\
		and theNumberOfChildrenInDependentTree[currentNode + direction] == 1\
		and theNumberOfChildrenInDependentTree[currentNode] == 0\
		and dependentTree[rootNode][currentNode + direction * 2] == 1\
		and theNumberOfChildrenInDependentTree[currentNode + direction * 2] == 0:
		return 2
	return 0

def findConstituent(currentRootNode: int, dependentTree: list, theNumberOfChildrenInDependentTree: list, theNumberOfWords: int, words: list)->list:
	leftToken = currentRootNode - 1
	while leftToken > 0:
		leftTokenIsLeaf = mergeCurrentNodeAndRoot(leftToken, currentRootNode, -1, dependentTree, theNumberOfChildrenInDependentTree, theNumberOfWords)
		if leftTokenIsLeaf == 0:
			break
		else:
			leftTokenMove = leftTokenIsLeaf
			leftToken -= leftTokenMove
	leftToken += 1

	rightToken = currentRootNode + 1
	while rightToken <= theNumberOfWords:
		step = mergeCurrentNodeAndRoot(rightToken, currentRootNode, 1, dependentTree, theNumberOfChildrenInDependentTree, theNumberOfWords)
		if step == 0:
			break
		else:
			rightToken += step
	rightToken -= 1
#	print(str(currentRootNode) + '\' (' + str(leftBound) + ' ' + str(rightToken) + ')')

	constituents = [(leftToken, rightToken)]
	for childNode in range(theNumberOfWords + 1):
		if childNode in range(leftToken, rightToken + 1) or dependentTree[currentRootNode][childNode] == 0:
			continue
		else:
			constituents = constituents + findConstituent(childNode, dependentTree, theNumberOfChildrenInDependentTree, theNumberOfWords, words)

	constituents = sorted(constituents)
	return constituents

def dependencyParsing(language:str, sentence:str, lineLimit:int):
	st.write('The length of the input sentence is:', len(sentence))
	nlp = stanza.Pipeline(lang = language, processors = 'tokenize, pos, lemma, depparse')
	doc = nlp(sentence)
#	print(*[f'word: {word.text}\tupos: {word.upos}\txpos: {word.xpos}\tfeats: {word.feats if word.feats else "_"}' for sent in doc.sentences for word in sent.words], sep='\n')
#	print(*[f'id: {word.id}\tword: {word.text}\thead id: {word.head}\thead: {sent.words[word.head-1].text if word.head > 0 else "root"}\tupos: {word.upos}' for sent in doc.sentences for word in sent.words], sep='\n')
	maxLength = max([max([len(word.text) for word in sentence.words]) for sentence in doc.sentences])
#	print(maxLength)
	if maxLength > lineLimit:
		st.write('The line limit is too small to split a sentence')
		return

#	print(len(doc.sentences))
#	print(len(POSdoc.sentences))
	for sentenceIdx in range(len(doc.sentences)):

		words = doc.sentences[sentenceIdx].words
		theNumberOfWords = len(words)
		isWordsDependent = [[0]*(theNumberOfWords + 1) for _ in range(theNumberOfWords + 1)]
		theNumberOfDependents = [0 for _ in range(theNumberOfWords + 1)]
		for word in words:
			if word.text not in puncList:
				isWordsDependent[word.head][word.id] = 1
				theNumberOfDependents[word.head] += 1
			else:
				isWordsDependent[word.id - 1][word.id] = 1
				theNumberOfDependents[word.id - 1] += 1

		currentRootNode = 0
		for index in range(theNumberOfWords + 1):
			if isWordsDependent[currentRootNode][index] == 1:
				currentRootNode = index
				break

		constituents = findConstituent(currentRootNode, isWordsDependent, theNumberOfDependents, theNumberOfWords, words)
	
		constituents = sorted(constituents)
		
#		print(constituents)

		idx = 0
		while idx < len(constituents):
			if idx == len(constituents) - 1:
				break
			currentInterval = constituents[idx]
			nextInterval = constituents[idx + 1]
			if (currentInterval[0] != currentInterval[1]) or words[idx].upos == 'VERB':
				idx += 1
				continue
			if isWordsDependent[currentInterval[1]][nextInterval[0]] == 1 or isWordsDependent[nextInterval[0]][currentInterval[1]] == 1:
				constituents.remove(currentInterval)
				constituents.remove(nextInterval)
				constituents.insert(idx, (currentInterval[0], nextInterval[1]))
			else:
				idx += 1
				
#		print(constituents)

# Deal with the long constituent
		constituentIdx = 0
		while constituentIdx < len(constituents):
			constituentLength = countConstituentsLength(constituentIdx, constituentIdx + 1, constituents, words, language)
			constituent = constituents[constituentIdx]
			head = constituent[0]
			tail = constituent[1]
			if lineLimit < constituentLength:
				constituents.remove(constituent)
				mid = int((head + tail) / 2)
				constituents.append((head, mid))
				constituents.append((mid + 1, tail))
				constituents = sorted(constituents)
			else:
				constituentIdx += 1
	
		constructLines(constituents, language, lineLimit, words)

	return

def constructLines(constituents:list, language:list, lineLimit:int, words:list):
	lines = []
	groupIndex = 0
	while groupIndex < len(constituents):
		remainLength = countConstituentsLength(groupIndex, len(constituents), constituents, words, language)
		if remainLength <= lineLimit:
#			print('one line section')
			lines.append(makeSentence(groupIndex, len(constituents), constituents, words, language))
			break
		if remainLength - 1 <= lineLimit * 2:
#			print('two line section')
			splitPoint = groupIndex
			bestLength = 0
			for candidateSplitPoint in range(groupIndex, len(constituents)):
				currentLength = countConstituentsLength(groupIndex, candidateSplitPoint, constituents, words, language)
				if currentLength <= lineLimit and (abs(currentLength * 2 - remainLength) < abs(bestLength * 2 - remainLength)):
					splitPoint = candidateSplitPoint
					bestLength = currentLength

			lines.append(makeSentence(groupIndex, splitPoint, constituents, words, language))
			groupIndex = splitPoint
		else:
			tailIndex = groupIndex
			currentLength = countConstituentsLength(groupIndex, tailIndex + 1, constituents, words, language)
			while currentLength <= lineLimit:
				tailIndex += 1
				currentLength = countConstituentsLength(groupIndex, tailIndex + 1, constituents, words, language)
					
			lines.append(makeSentence(groupIndex, tailIndex, constituents, words, language))
			groupIndex = tailIndex

	for idx in range(1, len(lines)):
		if lines[idx][0] in puncList:
			lines[idx - 1] += lines[idx][0]
			lines[idx] = lines[idx][1:]
			lines[idx] = lines[idx].strip()
			if len(lines[idx]) == 0:
				lines.remove(lines[idx])
				idx -= 1
				
#	st.write(lines)
	for lineIdx in range(len(lines)):
		st.write('Line ' + str(lineIdx) + ': ' + lines[lineIdx] + ' (' + str(len(lines[lineIdx])) + ')')
#		st.write('with length ' + str(len(lines[lineIdx])))
	return

def countConstituentsLength(headIndex, tailIndex, constituents, words, language):
	totalLength = 0
	wordNum = 0
	for constituentIndex in range(headIndex, tailIndex):
		for idx in range(constituents[constituentIndex][0] - 1, constituents[constituentIndex][1]):
			totalLength += len(words[idx].text)
			if words[idx].text not in puncList:
				wordNum += 1
			if words[idx].text in ['–', 'n\'t', '\'s', '\'d', 'n\'d', 'n’s', '’s', '’t']:
				wordNum -= 1
	if language in languageWithBlankSpace:
		totalLength += wordNum - 1
	return totalLength

def makeSentence(headIndex, tailIndex, constituents, words, language):
	sentence = ''
	for constituentIdx in range(headIndex, tailIndex):
		for wordIdx in range(constituents[constituentIdx][0] - 1, constituents[constituentIdx][1]):
			if (constituentIdx != headIndex or wordIdx != constituents[constituentIdx][0] - 1) and language in languageWithBlankSpace:
				sentence += ' '
			sentence += words[wordIdx].text
	sentence = sentence.strip()

	for punc in puncList:
		sentence = sentence.replace(' ' + punc, punc)
	sentence = sentence.replace(' – ', '–')
	sentence = sentence.replace('– ', '–')
	sentence = sentence.replace(' –', '–')
	sentence = sentence.replace(' n\'t', 'n\'t')
	sentence = sentence.replace(' \'s', '\'s')
	sentence = sentence.replace(' \'d', '\'d')
	sentence = sentence.replace(' n’t', 'n’t')
	sentence = sentence.replace(' ’s', '’s')
	sentence = sentence.replace(' ’d', '’d')
	
	return sentence

if __name__ == '__main__':
	st.title('Long Sentence Splitter')
	language = st.selectbox('Please select the language of input.', ['英文', '簡中', '繁中'])
	if language == '英文':
		language = 'en'
	elif language == '簡中':
		language = 'zh-hans'
	elif language == '繁中':
		language = 'zh-hant'
	sentence = st.text_input("Input Sentence:")
	lineLimit = int(st.text_input("Line limit:"))
	starts = st.button('run')
	if starts:
		dependencyParsing(language, sentence, lineLimit)
