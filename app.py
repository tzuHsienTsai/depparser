import stanza
import streamlit as st

puncList = ['.', ',', ':', ';', '!', '?', '\'', '\"', '，', '。', '：', '；', '！', '？']

def canMerge(bound:int, rootIndex:int, direction:int, dependentTree:list, theNumberOfChildrenInDependentTree:list, theNumberOfWords:int)->int:
	if dependentTree[rootIndex][bound] == 1 and theNumberOfChildrenInDependentTree[bound] == 0:
		return 1
	if bound >= rootIndex - 1 and bound <= rootIndex + 1:
		if bound + direction in range(0, theNumberOfWords + 1) and dependentTree[rootIndex][bound] == 1 and dependentTree[bound][bound + direction] == 1 and theNumberOfChildrenInDependentTree[bound] == 1 and theNumberOfChildrenInDependentTree[bound + direction] == 0:
			return 2
		elif bound + direction in range(0, theNumberOfWords + 1) and dependentTree[rootIndex][bound + direction] == 1 and dependentTree[bound + direction][bound] == 1 and theNumberOfChildrenInDependentTree[bound + direction] == 1 and theNumberOfChildrenInDependentTree[bound] == 0:
			return 2
	return 0

def findConstituent(currentRootIndex: int, dependentTree: list, theNumberOfChildrenInDependentTree: list, theNumberOfWords: int)->list:
	leftBound = currentRootIndex - 1
	while leftBound > 0:
		step = canMerge(leftBound, currentRootIndex, -1, dependentTree, theNumberOfChildrenInDependentTree, theNumberOfWords)
		if step == 0:
			break
		else:
			leftBound -= step
	leftBound += 1

	rightBound = currentRootIndex + 1
	while rightBound <= theNumberOfWords:
		step = canMerge(rightBound, currentRootIndex, 1, dependentTree, theNumberOfChildrenInDependentTree, theNumberOfWords)
		if step == 0:
			break
		else:
			rightBound += step
	rightBound -= 1

	ret = [(leftBound, rightBound)]
	for childIndex in range(theNumberOfWords + 1):
		if childIndex in range(leftBound, rightBound + 1) or dependentTree[currentRootIndex][childIndex] == 0:
			continue
		else:
			ret = ret + findConstituent(childIndex, dependentTree, theNumberOfChildrenInDependentTree, theNumberOfWords)

	return ret

def dependencyParsing(language:str, sentence:str, lineLimit:int):
	nlp = stanza.Pipeline(lang = language, processors = 'tokenize, pos, lemma, depparse')
	doc = nlp(sentence)

	POSTagger = stanza.Pipeline(lang=language, processors='tokenize,pos')
	POSdoc = nlp(sentence)
	print(*[f'word: {word.text}\tupos: {word.upos}\txpos: {word.xpos}\tfeats: {word.feats if word.feats else "_"}' for sent in doc.sentences for word in sent.words], sep='\n')
	POSOfWords = POSdoc.sentences[0].words

	print(*[f'id: {word.id}\tword: {word.text}\thead id: {word.head}\thead: {sent.words[word.head-1].text if word.head > 0 else "root"}\tdeprel: {word.deprel}' for sent in doc.sentences for word in sent.words], sep='\n')

	words = doc.sentences[0].words
	theNumberOfWords = len(words)
	#word.id, word.text, word.head
	isWordsDependent = [[0]*(theNumberOfWords + 1) for _ in range(theNumberOfWords + 1)]
	theNumberOfDependent = [0 for _ in range(theNumberOfWords + 1)]
	for word in words:
		isWordsDependent[word.head][word.id] = 1
		theNumberOfDependent[word.head] += 1
#	print(isWordsDependent)
#	print(theNumberOfDependent)

	currentRootIndex = 0
	for index in range(theNumberOfWords + 1):
		if isWordsDependent[currentRootIndex][index] == 1:
			currentRootIndex = index
			break

	availableBreakpoint = findConstituent(currentRootIndex, isWordsDependent, theNumberOfDependent, theNumberOfWords)
	
	availableBreakpoint = sorted(availableBreakpoint)

	idx = 0
	while idx < len(availableBreakpoint):
		if idx == len(availableBreakpoint) - 1:
			break
		currentInterval = availableBreakpoint[idx]
		nextInterval = availableBreakpoint[idx + 1]
		if (currentInterval[0] != currentInterval[1]) or POSOfWords[idx].upos == 'VERB':
			idx += 1
			continue
		if isWordsDependent[currentInterval[1]][nextInterval[0]] == 1 or isWordsDependent[nextInterval[0]][currentInterval[1]] == 1:
			availableBreakpoint.remove(currentInterval)
			availableBreakpoint.remove(nextInterval)
			availableBreakpoint.insert(idx, (currentInterval[0], nextInterval[1]))
		else:
			idx += 1
			
	print(availableBreakpoint)
	st.write('The length of the input sentence is:', len(sentence))
	lines = []
	groupIndex = 0
	currentLine = ''
	while groupIndex < len(availableBreakpoint):
		if doesntExceedLength(currentLine, words, availableBreakpoint[groupIndex], lineLimit):
			for idx in range(availableBreakpoint[groupIndex][0] - 1, availableBreakpoint[groupIndex][1]):
				if currentLine != '':
					currentLine += ' '
				currentLine += words[idx].text
			groupIndex += 1
		else:
			for punc in puncList:
				currentLine = currentLine.replace(' ' + punc, punc)
			lines.append(currentLine.strip())
			currentLine = ''
	if currentLine != '':
		for punc in puncList:
			currentLine = currentLine.replace(' ' + punc, punc)
		lines.append(currentLine.strip())
	
	for idx in range(1, len(lines)):
		if lines[idx][0] in puncList:
			lines[idx - 1] += lines[idx][0]
			lines[idx] = lines[idx][1:]
			while lines[idx][0] == ' ':
				if len(lines[idx]) == 1:
					lines.pop()
					break
				else:
					lines[idx] = lines[idx][1:]

	st.write('The input sentence is split into ' + str(len(lines)) + ' lines.')
	st.write(lines)
	st.write('Each of them is of length:')
	lineLength = [len(line) for line in lines]
	st.write(lineLength)
	return

def doesntExceedLength(line, words, wordRange, lineLimit):
	remainLength = lineLimit - len(line)
	for idx in range(wordRange[0] - 1, wordRange[1]):
		remainLength -= len(words[idx].text)
		if remainLength < lineLimit and words[idx].text not in puncList:
			remainLength -= 1
		if remainLength < 0:
			return False
	return True

if __name__ == '__main__':
	st.title('Long Sentence Splitter')
	language = st.selectbox('Please select the language of input.', ['en', 'zh', 'ja'])
	sentence = st.text_input("Input Sentence:")
	lineLimit = int(st.text_input("Line limit:"))
	dependencyParsing(language, sentence, lineLimit)
