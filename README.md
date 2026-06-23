# Dico Wallon - Dictionnaire Liégeois en ligne

Une application web moderne, interactive et responsive (optimisée pour ordinateurs et smartphones) permettant de rechercher instantanément des traductions et définitions dans le dictionnaire liégeois de Jean Haust (Tomes II et III).

Ce projet fonctionne entièrement côté client (Single-Page Application) pour une rapidité d'exécution instantanée (< 5ms de latence de recherche) et permet un hébergement en ligne 100% gratuit.

---

## Fonctionnalités

* 🔍 **Recherche instantanée** : Recherche tolérante aux accents, majuscules et caractères spéciaux du wallon. Classement des résultats par pertinence (termes exacts d'abord, puis débuts de mots, puis occurrences dans les définitions).
* 📅 **Le mot du jour** : Sélectionne automatiquement un mot wallon par jour de l'année pour encourager l'apprentissage quotidien.
* 💖 **Système de favoris** : Possibilité de sauvegarder ses mots préférés. La liste est conservée localement dans le navigateur (`localStorage`).
* ⏳ **Historique de recherche** : Affiche les dernières recherches effectuées pour y revenir en un clic.
* 📖 **Fidélité aux sources** : Chaque mot affiche son Tome (Tome II : Wallon-Français, Tome III : Français-Wallon) et sa page d'origine dans l'œuvre physique de Jean Haust pour faciliter les vérifications.
* 📱 **Optimisation Mobile** : Interface adaptative moderne avec thème sombre premium et effets visuels soignés.

---

## Structure du Projet

```text
dico-wallon/
├── index.html   # Structure HTML5 et métadonnées SEO
├── index.css    # Design system, thèmes, polices et animations responsive
├── app.js       # Logique de recherche, favoris, historique et mot du jour
└── dico.json    # Base de données unifiée (2 433 entrées de Jean Haust)
```

---

## Lancement en Local

Pour des raisons de sécurité du navigateur (règles CORS), le fichier `dico.json` ne peut pas être lu directement en double-cliquant sur `index.html`. Vous devez lancer un petit serveur local.

### Option 1 : Avec Python (recommandé et pré-installé)
1. Ouvrez un terminal (PowerShell ou CMD) dans le dossier `dico-wallon`.
2. Lancez la commande suivante :
   ```bash
   python -m http.server 8000
   ```
3. Ouvrez votre navigateur sur [http://localhost:8000](http://localhost:8000).

### Option 2 : Avec une extension IDE
Si vous utilisez VS Code ou un IDE similaire, vous pouvez installer l'extension **Live Server** et cliquer sur "Go Live" en bas à droite pour ouvrir le projet.

---

## Hébergement en Ligne Gratuit (Zéro frais)

Voici trois méthodes simples et 100% gratuites pour mettre votre dictionnaire en ligne :

### Méthode A : Netlify (Le plus simple, sans code - Drag & Drop)
1. Allez sur le site de [Netlify](https://www.netlify.com/) et créez un compte gratuit (ou connectez-vous).
2. Rendez-vous sur la page **Netlify Drop** (ou dans l'onglet Deploy).
3. Glissez-déposez simplement l'intégralité du dossier `dico-wallon` dans la zone de téléchargement sur leur site.
4. Netlify déploie votre site instantanément et vous fournit un lien public (que vous pourrez ensuite personnaliser gratuitement ou lier à votre propre nom de domaine).

### Méthode B : GitHub Pages (Idéal si vous utilisez Git)
1. Créez un dépôt public sur votre compte GitHub (ex: `dico-wallon`).
2. Poussez les fichiers du dossier `dico-wallon` sur la branche principale (`main`).
3. Dans les paramètres de votre dépôt GitHub (**Settings**) :
   * Allez dans l'onglet **Pages** (dans le menu de gauche).
   * Sous la section *Build and deployment*, choisissez *Deploy from a branch*.
   * Sélectionnez la branche `main` et le dossier `/ (root)`, puis cliquez sur **Save**.
4. Votre dictionnaire sera publié gratuitement à l'adresse `https://<votre-nom-d-utilisateur>.github.io/dico-wallon/`.

### Méthode C : Vercel (Via la ligne de commande)
1. Installez Vercel en ligne de commande :
   ```bash
   npm install -g vercel
   ```
2. Ouvrez votre terminal dans le dossier `dico-wallon` et tapez :
   ```bash
   vercel
   ```
3. Suivez les instructions rapides à l'écran. Votre site est déployé en moins d'une minute sur un serveur ultra-rapide.
