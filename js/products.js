/* ============================================================
   CATALOGUE — pour ajouter une raquette : copiez un bloc { ... }
   et collez-le dans la liste, puis changez les valeurs.
   (Le plus simple : utiliser le mode Admin du site, puis "Exporter".)

   etat      : "Neuf" | "Très bon état"
   stock     : quantité disponible. Stock 0 = raquette masquée du site.
   poids     : ex "365 g"
   forme     : "Diamant" | "Goutte d'eau" | "Ronde"
   niveau    : "Débutant" | "Intermédiaire" | "Confirmé" | "Expert"
   equilibre : "Bas" | "Moyen" | "Haut"
   materiau, annee : texte libre
   description : note facultative
   images    : chemins des photos (la 1re = photo principale)
   ============================================================ */
window.PRODUCTS = [
  {
    "id": "bullpadel-vertex-04",
    "nom": "Bullpadel Vertex 04",
    "marque": "Bullpadel",
    "prix": 189,
    "stock": 1,
    "etat": "Très bon état",
    "poids": "365 g",
    "forme": "Diamant",
    "niveau": "Confirmé",
    "equilibre": "Haut",
    "materiau": "Carbone 12K",
    "annee": "2023",
    "description": "Raquette de puissance au toucher ferme, idéale pour les joueurs offensifs. Quelques micro-marques d'usure sur le cadre, aucun impact sur le jeu. Livrée avec housse.",
    "images": [
      "assets/img/raquette-1-a.svg",
      "assets/img/raquette-1-b.svg"
    ]
  },
  {
    "id": "nox-at10-genius",
    "nom": "NOX AT10 Genius 18K",
    "marque": "NOX",
    "prix": 229,
    "stock": 3,
    "etat": "Neuf",
    "poids": "360 g",
    "forme": "Goutte d'eau",
    "niveau": "Confirmé",
    "equilibre": "Moyen",
    "materiau": "Carbone 18K",
    "annee": "2024",
    "description": "Modèle neuf, jamais utilisé, sous emballage d'origine. Excellent compromis puissance / confort grâce au carbone 18K.",
    "images": [
      "assets/img/raquette-2-a.svg",
      "assets/img/raquette-2-b.svg"
    ]
  },
  {
    "id": "adidas-metalbone-3-3",
    "nom": "Adidas Metalbone 3.3",
    "marque": "Adidas",
    "prix": 169,
    "stock": 1,
    "etat": "Très bon état",
    "poids": "365 g",
    "forme": "Diamant",
    "niveau": "Avancé",
    "equilibre": "Haut",
    "materiau": "Carbone",
    "annee": "2023",
    "description": "Une référence de la puissance. Très bon état général, grip neuf. Réservée en attente de récupération.",
    "images": [
      "assets/img/raquette-3-a.svg",
      "assets/img/raquette-3-b.svg"
    ]
  },
  {
    "id": "head-delta-pro",
    "nom": "Head Delta Pro",
    "marque": "Head",
    "prix": 119,
    "stock": 2,
    "etat": "Très bon état",
    "poids": "355 g",
    "forme": "Ronde",
    "niveau": "Débutant / Intermédiaire",
    "equilibre": "Bas",
    "materiau": "Fibre de verre",
    "annee": "2022",
    "description": "Raquette polyvalente et maniable, parfaite pour progresser. Traces d'utilisation visibles mais structure saine.",
    "images": [
      "assets/img/raquette-4-a.svg",
      "assets/img/raquette-4-b.svg"
    ]
  },
  {
    "id": "babolat-technical-viper",
    "nom": "Babolat Technical Viper",
    "marque": "Babolat",
    "prix": 149,
    "stock": 0,
    "etat": "Très bon état",
    "poids": "365 g",
    "forme": "Diamant",
    "niveau": "Confirmé",
    "equilibre": "Haut",
    "materiau": "Carbone",
    "annee": "2022",
    "description": "Raquette de puissance utilisée quelques mois seulement.",
    "images": [
      "assets/img/raquette-5-a.svg",
      "assets/img/raquette-5-b.svg"
    ]
  }
];
