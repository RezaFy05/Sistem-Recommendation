import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.neighbors import KNeighborsClassifier
from preprocessing import preprocess_text

def jaccard_similarity(str1, str2):
    set1, set2 = set(str1.split()), set(str2.split())
    return len(set1 & set2) / len(set1 | set2) if set1 | set2 else 0

def get_recommendation(input_text):
    # Membaca data dari database
    engine = create_engine("mysql+mysqlconnector://root:@localhost/db_coba")
    query = "SELECT judul, bidang_minat, fileName FROM jurnal_files"
    df = pd.read_sql(query, con=engine)

    # Preprocessing judul jurnal dan input_text
    df['processed'] = df['judul'].fillna("").apply(preprocess_text)
    input_preprocessed = preprocess_text(input_text)
    
    # Debug: cek apakah preprocessing input_text menghasilkan nilai yang baik
    print("Input Text After Preprocessing:", input_preprocessed)

    # Hitung similarity antara input_text dan judul jurnal
    df['similarity'] = df['processed'].apply(lambda x: jaccard_similarity(input_preprocessed, x))

    # Filter hasil berdasarkan threshold similarity
    SIMILARITY_THRESHOLD = 0.1  # Turunkan threshold untuk menghindari terlalu sedikit hasil
    filtered_docs = df[df['similarity'] >= SIMILARITY_THRESHOLD]

    if filtered_docs.empty:
        return []  # Jika tidak ada hasil yang sesuai, return kosong

    # Ambil 20 hasil teratas berdasarkan similarity
    top_docs = filtered_docs.sort_values(by='similarity', ascending=False).head(20)

    # Buat vektor biner berdasarkan vocabulary
    vocabulary = sorted(set(word for doc in top_docs['processed'] for word in doc.split()))
    top_docs['binary_vector'] = top_docs['processed'].apply(
        lambda x: [1 if word in x.split() else 0 for word in vocabulary]
    )

    X = np.array(top_docs['binary_vector'].tolist())
    y = top_docs['bidang_minat']

    # KNN (K-Nearest Neighbors)
    n_neighbors = min(5, len(top_docs))
    if n_neighbors == 0:
        return []

    knn = KNeighborsClassifier(n_neighbors=n_neighbors)
    knn.fit(X, y)

    # Vektor input untuk mencari tetangga terdekat
    input_vec = [1 if word in input_preprocessed.split() else 0 for word in vocabulary]
    neighbors = knn.kneighbors([input_vec], return_distance=False)[0]

    # Ambil hasil akhir rekomendasi
    results = []
    for idx in neighbors:
        row = top_docs.iloc[idx]
        results.append({
            'judul': row['judul'],
            'bidang_minat': row['bidang_minat'],
            'similarity': row['similarity'],
            'fileName': row['fileName']
        })

    return results
