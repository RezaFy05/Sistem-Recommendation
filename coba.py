from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

text = "Saya sedang belajar pemrograman Python dengan NLTK"
tokens = word_tokenize(text)
filtered = [word for word in tokens if word.lower() not in stopwords.words('indonesian')]

print("Token:", tokens)
print("Setelah filtering:",filtered)