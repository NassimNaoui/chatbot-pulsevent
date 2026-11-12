from src.chatbot_pulsevent.config import Config
from mistralai import Mistral
from tqdm import tqdm
import pandas as pd
import pickle
import os
import json
import time

class Transform:
    def __init__(self):
        self.config = Config()
        
        self.api_key = self.config.MISTRAL_API_KEY
        self.client = Mistral(api_key=self.api_key)

    def read_file(self, json_file: dict) -> dict:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def flatten_json(self, dictionay : dict) -> pd.DataFrame:
        df = pd.json_normalize(dictionay['events'])

        col_to_kepp = [
            'dateRange.fr',
            'description.fr',
            'image.base',
            'image.filename',
            'keywords.fr',
            'location.address',
            'location.city',
            'location.latitude',
            'location.longitude',
            'location.name',
            'location.uid', 
            'lastTiming.begin',
            'lastTiming.end',
            'nextTiming.begin',
            'nextTiming.end',
            'slug',
            'timezone'
         ]

        df_clean = df[col_to_kepp].copy()

        df_clean = df_clean.rename(columns={
            'dateRange.fr': 'dateRange',
            'description.fr': 'description',
            'keywords.fr': 'keywords',
            'location.uid': 'location.uuid' 
        })

        return df_clean

    def prepare_text_for_embedding(self, row: pd.Series) -> str:
        """
        Concatène les métadonnées utiles et la description pour donner 
        un contexte complet au modèle de vectorisation.
        """
        # Remplacement des valeurs nulles par des chaînes vides pour éviter les erreurs
        titre = str(row.get('slug', '')).replace('-', ' ')
        date = str(row.get('dateRange', ''))
        lieu_nom = str(row.get('location.name', ''))
        ville = str(row.get('location.city', ''))
        mots_cles = str(row.get('keywords', ''))
        description = str(row.get('description', 'Description is missing'))
        
        # Construction du texte formaté
        texte_complet = (
            f"Titre de l'événement : {titre}\n"
            f"Dates : {date}\n"
            f"Lieu : {lieu_nom}, {ville}\n"
            f"Mots-clés : {mots_cles}\n"
            f"Description : {description}"
        )
        return texte_complet

    def vectorise_by_batch(self, liste_textes, BATCH_SIZE=100, DELAY=1, MAX_RETRIES=3):
        # Chemin vers le fichier de sauvegarde temporaire
        checkpoint_path = self.config.PROCESSED_DATA_DIR / "vectors_checkpoint.pkl"
        
        all_vectors = []
        start_index = 0
        
        # 1. Reprise depuis la sauvegarde si elle existe
        if checkpoint_path.exists():
            print(f"Reprise à partir de la sauvegarde : {checkpoint_path}")
            with open(checkpoint_path, 'rb') as f:
                all_vectors = pickle.load(f)
            start_index = len(all_vectors)
            print(f"{start_index} textes déjà vectorisés. Reprise au texte {start_index}...")

        # Si tout était déjà fini
        if start_index >= len(liste_textes):
            return all_vectors

        # Calcul pour la barre de progression tqdm afin qu'elle s'affiche correctement
        total_batches = (len(liste_textes) + BATCH_SIZE - 1) // BATCH_SIZE
        initial_batch = start_index // BATCH_SIZE

        # 2. Boucle de vectorisation en reprenant au bon index
        for i in tqdm(
            range(start_index, len(liste_textes), BATCH_SIZE), 
            desc="Vectorisation", 
            initial=initial_batch, 
            total=total_batches
        ):
            batch = liste_textes[i : i + BATCH_SIZE]
            succes = False
            essais = 0
            
            while not succes and essais < MAX_RETRIES:
                try:
                    reponse = self.client.embeddings.create(
                        model="mistral-embed",
                        inputs=batch
                    )
                    all_vectors.extend([element.embedding for element in reponse.data])
                    succes = True
                    time.sleep(DELAY)
                    
                except Exception as e:
                    essais += 1
                    print(f"\nErreur au batch index {i} (Essai {essais}/{MAX_RETRIES}) : {e}")
                    time.sleep(5 * essais)
                    
            if not succes:
                print(f"\nÉchec définitif pour l'index {i}. Valeurs nulles insérées.")
                all_vectors.extend([None] * len(batch))
                
            # 3. Sauvegarde intermédiaire tous les 50 batchs
            current_batch = (i // BATCH_SIZE) + 1
            if current_batch % 50 == 0:
                with open(checkpoint_path, 'wb') as f:
                    pickle.dump(all_vectors, f)
                
        # 4. Nettoyage : suppression du fichier temporaire une fois la vectorisation totalement terminée
        if checkpoint_path.exists():
            os.remove(checkpoint_path)
            
        return all_vectors

if __name__ == "__main__":
    runner = Transform()

    json_path = runner.config.RAW_DATA_DIR / "openAgendaData.json"

    # 1. Lecture et nettoyage
    data = runner.read_file(json_path)
    df = runner.flatten_json(data)
    df["description"] = df["description"].fillna("Description is missing")
    
    # 2. Création de la nouvelle colonne de texte enrichi
    df["full_context"] = df.apply(runner.prepare_text_for_embedding, axis=1)
    
    # 3. Vectorisation basée sur le texte enrichi 
    df["mistral_vectors"] = runner.vectorise_by_batch(df["full_context"].to_list())
    
    # 4. Sauvegarde
    df.to_pickle(runner.config.PROCESSED_DATA_DIR / "dataframe_with_vectors.pkl")