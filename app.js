// li ptit motî walon - Premium Application Logic

// Application State
let dictionary = [];
let filteredResults = [];
let favorites = new Set();
let searchHistory = [];
let itemsLimit = 50;
let isExpanded = false; // State to track search expansion (only show 1 result initially)

// DOM Elements
const searchBox = document.getElementById('search-box');
const clearSearchBtn = document.getElementById('clear-search');
const resultsList = document.getElementById('results-list');
const resultsLabel = document.getElementById('results-label');
const resultsCount = document.getElementById('results-count');
const favoritesList = document.getElementById('favorites-list');
const historyList = document.getElementById('history-list');

// Tabs
const tabAll = document.getElementById('tab-all');
const tabW2F = document.getElementById('tab-w2f');
const tabF2W = document.getElementById('tab-f2w');
let currentFilter = 'all';

// Modal Elements
const detailModal = document.getElementById('detail-modal');
const modalWord = document.getElementById('modal-word');
const modalBadge = document.getElementById('modal-badge');
const modalDefinition = document.getElementById('modal-definition');
const modalRefTome = document.getElementById('modal-ref-tome');
const modalRefPage = document.getElementById('modal-ref-page');
const modalFavBtn = document.getElementById('modal-fav-btn');
const closeModalBtn = document.getElementById('close-modal');

// Accent Normalization Utility
function removeAccents(str) {
  if (!str) return '';
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/œ/g, "oe")
    .replace(/æ/g, "ae")
    .replace(/[åå]/g, "a") // Wallon ringed-a
    .replace(/[îî]/g, "i")
    .replace(/[ôô]/g, "o")
    .replace(/[ûû]/g, "u")
    .replace(/[êê]/g, "e")
    .replace(/[èè]/g, "e")
    .replace(/[éé]/g, "e")
    .replace(/[ââ]/g, "a")
    .toLowerCase();
}

// Extract Main Translation for display next to the headword
function extractMainTranslation(entry) {
  if (!entry) return '';
  if (entry.definitions && entry.definitions.length > 0) {
    return entry.definitions[0];
  }
  // Fallback
  if (entry.definition) {
    return entry.definition.split(/[:;,.]/)[0].trim();
  }
  return '';
}

// LCG Pseudo-Random Generator (seeded by date for consistent daily word)
function getDailySeed() {
  const today = new Date();
  return today.getFullYear() * 10000 + (today.getMonth() + 1) * 100 + today.getDate();
}

function getWordOfTheDay(dict) {
  if (!dict || dict.length === 0) return null;
  const seed = getDailySeed();
  let r = seed;
  r = (r * 1664525 + 1013904223) % 4294967296;
  const index = Math.abs(r) % dict.length;
  return dict[index];
}

// Generate unique key for entries to identify in favorites
function getEntryKey(entry) {
  return `${entry.mot}_T${entry.tome}_P${entry.page}_${entry.type}`;
}

// Initialize Application
async function init() {
  try {
    if (window.dictionaryData && window.dictionaryData.length > 0) {
      dictionary = window.dictionaryData;
    } else {
      const response = await fetch('dico.json');
      if (!response.ok) throw new Error("Impossible de charger dico.json");
      dictionary = await response.json();
    }
    
    // Load Favorites & History from LocalStorage
    loadFavorites();
    loadHistory();
    
    // Render Widgets
    setupWordOfTheDay();
    renderFavorites();
    renderHistory();
    
    // Set initial display
    performSearch();
    
    // Attach Event Listeners
    setupEventListeners();
  } catch (error) {
    console.error("Erreur d'initialisation:", error);
    resultsList.innerHTML = `
      <div class="empty-state" style="color: var(--accent-red-text);">
        <i class="fa-solid fa-triangle-exclamation" style="font-size: 2.5rem; margin-bottom: 1rem;"></i>
        <p>Erreur lors du chargement des données. Veuillez recharger la page.</p>
        <p style="font-size: 0.8rem; margin-top: 0.5rem; opacity: 0.7;">${error.message}</p>
      </div>
    `;
  }
}

// Load / Save Favorites
function loadFavorites() {
  const stored = localStorage.getItem('dico_favorites');
  if (stored) {
    favorites = new Set(JSON.parse(stored));
  }
}

function saveFavorites() {
  localStorage.setItem('dico_favorites', JSON.stringify(Array.from(favorites)));
}

// Load / Save History
function loadHistory() {
  const stored = localStorage.getItem('dico_history');
  if (stored) {
    searchHistory = JSON.parse(stored);
  }
}

function saveHistory(query) {
  if (!query || query.trim() === '') return;
  const cleaned = query.trim();
  
  searchHistory = searchHistory.filter(item => item.toLowerCase() !== cleaned.toLowerCase());
  searchHistory.unshift(cleaned);
  
  if (searchHistory.length > 8) {
    searchHistory.pop();
  }
  
  localStorage.setItem('dico_history', JSON.stringify(searchHistory));
  renderHistory();
}

function clearHistory() {
  searchHistory = [];
  localStorage.removeItem('dico_history');
  renderHistory();
}

// Render Bookmarks / Favorites in Sidebar
function renderFavorites() {
  favoritesList.innerHTML = '';
  
  const favEntries = dictionary.filter(entry => favorites.has(getEntryKey(entry)));
  
  if (favEntries.length === 0) {
    favoritesList.innerHTML = '<div class="empty-state">Aucun favori enregistré.</div>';
    return;
  }
  
  favEntries.forEach(entry => {
    const item = document.createElement('div');
    item.className = 'bookmark-item';
    
    const label = document.createElement('span');
    // Distinguish fonts in bookmarks
    label.className = `bookmark-word ${entry.type === 'wallon-francais' ? 'wallon-text' : 'francais-text'}`;
    label.style.fontSize = '0.95rem';
    label.textContent = entry.mot;
    label.addEventListener('click', () => openDetailModal(entry));
    
    const removeBtn = document.createElement('button');
    removeBtn.className = 'remove-bookmark-btn';
    removeBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
    removeBtn.title = "Retirer des favoris";
    removeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleFavorite(entry);
    });
    
    item.appendChild(label);
    item.appendChild(removeBtn);
    favoritesList.appendChild(item);
  });
}

// Render Search History in Sidebar
function renderHistory() {
  historyList.innerHTML = '';
  
  if (searchHistory.length === 0) {
    historyList.innerHTML = '<div class="empty-state">Aucune recherche récente.</div>';
    return;
  }
  
  searchHistory.forEach(query => {
    const item = document.createElement('div');
    item.className = 'history-item';
    item.innerHTML = `<i class="fa-solid fa-magnifying-glass" style="font-size: 0.75rem;"></i> <span>${query}</span>`;
    item.addEventListener('click', () => {
      searchBox.value = query;
      clearSearchBtn.style.display = 'block';
      isExpanded = false; // Reset expand on click history
      performSearch();
    });
    historyList.appendChild(item);
  });
  
  const clearBtn = document.createElement('button');
  clearBtn.className = 'tab-btn';
  clearBtn.style.marginTop = '0.75rem';
  clearBtn.style.width = '100%';
  clearBtn.style.justifyContent = 'center';
  clearBtn.style.fontSize = '0.8rem';
  clearBtn.style.padding = '0.5rem';
  clearBtn.innerHTML = '<i class="fa-solid fa-eraser"></i> Effacer l\'historique';
  clearBtn.addEventListener('click', clearHistory);
  historyList.appendChild(clearBtn);
}

// Word of the Day logic
function setupWordOfTheDay() {
  const mot = getWordOfTheDay(dictionary);
  const container = document.getElementById('mot-du-jour-container');
  
  if (!mot) {
    container.innerHTML = '<div class="empty-state">Données indisponibles.</div>';
    return;
  }
  
  const mainTranslation = extractMainTranslation(mot);
  const transClass = mot.type === 'wallon-francais' ? 'francais-text' : 'wallon-text';
  
  container.innerHTML = `
    <div style="display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.5rem;">
      <div class="mot-word" id="mot-du-jour-word">${mot.mot}</div>
      <span class="word-translation ${transClass}" id="mot-du-jour-trans" style="cursor: pointer;">— ${mainTranslation}</span>
    </div>
    <div class="badge ${mot.type === 'wallon-francais' ? 'badge-w2f' : 'badge-f2w'}" style="margin-top: 0.25rem; margin-bottom: 0.5rem; display: inline-block;">
      ${mot.type === 'wallon-francais' ? 'Wallon' : 'Français'}
    </div>
    <div class="mot-definition" style="margin-top: 0.25rem;">
      ${formatDefinitionText(mot)}
    </div>
  `;
  
  document.getElementById('mot-du-jour-word').addEventListener('click', () => openDetailModal(mot));
  document.getElementById('mot-du-jour-trans').addEventListener('click', () => openDetailModal(mot));
}

// Parse structured dictionary entries into premium HTML
function formatDefinitionText(entry) {
  if (!entry) return '';
  
  let html = '';
  
  // 1. Grammaire, Genre, Prononciation, Domaines
  let metaParts = [];
  if (entry.categorie) {
    metaParts.push(`<span class="meta-item cat">${entry.categorie}</span>`);
  }
  if (entry.genre) {
    metaParts.push(`<span class="meta-item gen">${entry.genre}</span>`);
  }
  if (entry.prononciation) {
    metaParts.push(`<span class="meta-item pron">[${entry.prononciation}]</span>`);
  }
  if (entry.domaines && entry.domaines.length > 0) {
    entry.domaines.forEach(d => {
      metaParts.push(`<span class="meta-item dom">${d}</span>`);
    });
  }
  
  if (metaParts.length > 0) {
    html += `<div class="entry-meta-container">${metaParts.join(' ')}</div>`;
  }
  
  // 2. Définitions
  if (entry.definitions && entry.definitions.length > 0) {
    html += `<div class="def-block">`;
    if (entry.definitions.length === 1) {
      html += `<p class="def-text">${entry.definitions[0]}</p>`;
    } else {
      html += `<ol class="def-list">`;
      entry.definitions.forEach(d => {
        html += `<li>${d}</li>`;
      });
      html += `</ol>`;
    }
    html += `</div>`;
  }
  
  // 3. Exemples
  if (entry.exemples && entry.exemples.length > 0) {
    html += `<div class="exemples-block">`;
    html += `<h4 class="section-title"><i class="fa-solid fa-quote-left"></i> Exemples</h4>`;
    html += `<ul class="exemples-list">`;
    entry.exemples.forEach(ex => {
      let wal = ex.wallon.replace(/~/g, `<strong class="headword-highlight">${entry.mot}</strong>`);
      let fra = ex.francais ? `<span class="example-translation">— ${ex.francais}</span>` : '';
      html += `<li><span class="example-wal">${wal}</span> ${fra}</li>`;
    });
    html += `</ul>`;
    html += `</div>`;
  }
  
  // 4. Expressions
  if (entry.expressions && entry.expressions.length > 0) {
    html += `<div class="expressions-block">`;
    html += `<h4 class="section-title"><i class="fa-solid fa-share-nodes"></i> Expressions</h4>`;
    html += `<ul class="expressions-list">`;
    entry.expressions.forEach(expr => {
      html += `<li><span class="expr-text">${expr}</span></li>`;
    });
    html += `</ul>`;
    html += `</div>`;
  }
  
  // 5. Synonymes
  if (entry.synonymes && entry.synonymes.length > 0) {
    html += `<div class="syn-block">`;
    html += `<span class="label">Synonymes :</span> `;
    let synLinks = entry.synonymes.map(s => `<span class="ref-link" onclick="window.openWordByName('${s.replace(/'/g, "\\'")}')">${s}</span>`);
    html += synLinks.join(', ');
    html += `</div>`;
  }
  
  // 6. Renvois
  if (entry.renvois && entry.renvois.length > 0) {
    html += `<div class="renvois-block">`;
    html += `<span class="label">Voir aussi :</span> `;
    let renvoiLinks = entry.renvois.map(r => `<span class="ref-link" onclick="window.openWordByName('${r.replace(/'/g, "\\'")}')">${r}</span>`);
    html += renvoiLinks.join(', ');
    html += `</div>`;
  }
  
  // 7. Origine / Étymologie
  if (entry.origine) {
    html += `<div class="origine-block">`;
    html += `<span class="label">Étymologie :</span> <span class="origine-text">${entry.origine}</span>`;
    html += `</div>`;
  }
  
  return html;
}

// Search Algorithm and Ranking
function performSearch() {
  const query = searchBox.value.trim();
  const normalizedQuery = removeAccents(query);
  
  // Reset scroll limit
  itemsLimit = 50;
  
  if (normalizedQuery === '') {
    filteredResults = dictionary;
    if (currentFilter !== 'all') {
      filteredResults = filteredResults.filter(entry => entry.type === currentFilter);
    }
    filteredResults.sort((a, b) => a.mot.localeCompare(b.mot));
    resultsLabel.textContent = currentFilter === 'all' ? "Toutes les entrées" : (currentFilter === 'wallon-francais' ? "Entrées Wallon-Français" : "Entrées Français-Wallon");
  } else {
    const scored = [];
    
    for (let i = 0; i < dictionary.length; i++) {
      const entry = dictionary[i];
      
      if (currentFilter !== 'all' && entry.type !== currentFilter) continue;
      
      const normWord = removeAccents(entry.mot);
      const definitionsText = (entry.definitions || []).join(' ');
      const exemplesText = (entry.exemples || []).map(ex => ex.wallon + ' ' + ex.francais).join(' ');
      const synonymesText = (entry.synonymes || []).join(' ');
      const renvoisText = (entry.renvois || []).join(' ');
      const normDef = removeAccents(`${definitionsText} ${exemplesText} ${synonymesText} ${renvoisText}`);
      
      let score = 0;
      
      if (normWord === normalizedQuery) {
        score = 100;
      } else if (normWord.startsWith(normalizedQuery)) {
        score = 80;
      } else if (normWord.includes(normalizedQuery)) {
        score = 50;
      } else if (normDef.includes(normalizedQuery)) {
        score = 20;
      }
      
      if (score > 0) {
        scored.push({ entry, score });
      }
    }
    
    scored.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      if (a.entry.mot.length !== b.entry.mot.length) return a.entry.mot.length - b.entry.mot.length;
      return a.entry.mot.localeCompare(b.entry.mot);
    });
    
    filteredResults = scored.map(item => item.entry);
    resultsLabel.textContent = `Résultats pour "${query}"`;
  }
  
  resultsCount.textContent = filteredResults.length;
  renderResults();
}

// Render Results List (handles search collapse / expand)
function renderResults() {
  resultsList.innerHTML = '';
  const query = searchBox.value.trim();
  
  if (filteredResults.length === 0) {
    resultsList.innerHTML = `
      <div class="empty-state" style="padding: 3rem 0;">
        <i class="fa-solid fa-magnifying-glass-minus" style="font-size: 2.5rem; color: var(--text-muted); margin-bottom: 1rem;"></i>
        <p>Aucun mot trouvé dans la base.</p>
        <p style="font-size: 0.85rem; margin-top: 0.5rem; color: var(--text-muted);">Essayez avec un autre mot, ou vérifiez l'orthographe.</p>
      </div>
    `;
    return;
  }
  
  // Decide how many results to display initially
  // If there is an active search query, and we are NOT expanded: only show 1 result!
  const hasActiveQuery = query !== '';
  let toRender = [];
  
  if (hasActiveQuery && !isExpanded) {
    toRender = filteredResults.slice(0, 1);
  } else {
    toRender = filteredResults.slice(0, itemsLimit);
  }
  
  toRender.forEach(entry => {
    const key = getEntryKey(entry);
    const isFav = favorites.has(key);
    
    const card = document.createElement('div');
    card.className = 'dico-card';
    card.addEventListener('click', () => openDetailModal(entry));
    
    // Choose font family based on word language
    const wordClass = entry.type === 'wallon-francais' ? 'wallon-text' : 'francais-text';
    
    const mainTranslation = extractMainTranslation(entry);
    const transClass = entry.type === 'wallon-francais' ? 'francais-text' : 'wallon-text';
    
    card.innerHTML = `
      <div class="card-top">
        <div style="display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.5rem;">
          <span class="card-word ${wordClass}">${entry.mot}</span>
          <span class="word-translation ${transClass}">— ${mainTranslation}</span>
        </div>
        <span class="badge ${entry.type === 'wallon-francais' ? 'badge-w2f' : 'badge-f2w'}">
          ${entry.type === 'wallon-francais' ? 'Wallon' : 'Français'}
        </span>
      </div>
      <p class="card-definition">${formatDefinitionText(entry)}</p>
      <div class="card-footer">
        <div class="card-reference">
          <i class="fa-solid fa-book-open" style="font-size: 0.75rem; opacity: 0.7;"></i> 
          <span>Page ${entry.page}</span>
        </div>
        <button class="favorite-btn ${isFav ? 'active' : ''}" data-key="${key}" title="Ajouter aux favoris">
          <i class="fa-solid fa-heart"></i>
        </button>
      </div>
    `;
    
    const favBtn = card.querySelector('.favorite-btn');
    favBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleFavorite(entry);
    });
    
    resultsList.appendChild(card);
  });
  
  // If there is an active search query, more than 1 result, and we are NOT expanded:
  // Show a prominent "Chercher plus" (Dérouler) button
  if (hasActiveQuery && !isExpanded && filteredResults.length > 1) {
    const expandBtn = document.createElement('button');
    expandBtn.className = 'tab-btn expand-results-btn';
    expandBtn.style.width = '100%';
    expandBtn.style.justifyContent = 'center';
    expandBtn.style.padding = '1.25rem';
    expandBtn.style.marginTop = '1rem';
    expandBtn.style.fontFamily = 'var(--font-title)';
    expandBtn.style.fontSize = '1.05rem';
    expandBtn.style.fontWeight = '700';
    expandBtn.innerHTML = `<i class="fa-solid fa-circle-plus" style="margin-right: 0.5rem; color: var(--accent-gold-text);"></i> Chercher plus (${filteredResults.length - 1} autres réponses)`;
    
    expandBtn.addEventListener('click', () => {
      isExpanded = true;
      renderResults();
    });
    
    resultsList.appendChild(expandBtn);
  }
  
  // If we are expanded (or query is empty) and there are more than current limit:
  // Show the standard "Afficher plus" scroll loader button
  if ((!hasActiveQuery || isExpanded) && filteredResults.length > itemsLimit) {
    const loadMoreBtn = document.createElement('button');
    loadMoreBtn.className = 'tab-btn';
    loadMoreBtn.style.width = '100%';
    loadMoreBtn.style.justifyContent = 'center';
    loadMoreBtn.style.padding = '1rem';
    loadMoreBtn.style.marginTop = '0.5rem';
    loadMoreBtn.innerHTML = `<i class="fa-solid fa-circle-chevron-down"></i> Afficher plus de résultats (${filteredResults.length - itemsLimit} restants)`;
    loadMoreBtn.addEventListener('click', () => {
      itemsLimit += 50;
      renderResults();
    });
    resultsList.appendChild(loadMoreBtn);
  }
}

// Toggle Favorites status
function toggleFavorite(entry) {
  const key = getEntryKey(entry);
  if (favorites.has(key)) {
    favorites.delete(key);
  } else {
    favorites.add(key);
  }
  
  saveFavorites();
  renderFavorites();
  
  const btns = document.querySelectorAll(`.favorite-btn[data-key="${key}"]`);
  btns.forEach(btn => {
    btn.classList.toggle('active', favorites.has(key));
  });
  
  if (detailModal.classList.contains('active')) {
    const modalKey = modalFavBtn.getAttribute('data-key');
    if (modalKey === key) {
      modalFavBtn.classList.toggle('active', favorites.has(key));
    }
  }
}

// Modal View Details
// Clickable Renvois / Synonymes Navigation
window.openWordByName = function(wordName) {
  if (!wordName) return;
  const cleanedName = wordName.trim();
  const match = dictionary.find(e => removeAccents(e.mot) === removeAccents(cleanedName));
  if (match) {
    openDetailModal(match);
  } else {
    // Si pas trouvé précisément, lancer une recherche sur le mot
    searchBox.value = cleanedName;
    clearSearchBtn.style.display = 'block';
    isExpanded = false;
    performSearch();
    closeDetailModal();
  }
};

// Modal View Details
let activeModalEntry = null;

function openDetailModal(entry) {
  activeModalEntry = entry;
  const key = getEntryKey(entry);
  const isFav = favorites.has(key);
  
  const mainTranslation = extractMainTranslation(entry);
  const transClass = entry.type === 'wallon-francais' ? 'francais-text' : 'wallon-text';
  
  modalWord.innerHTML = `${entry.mot} <span class="word-translation ${transClass}">— ${mainTranslation}</span>`;
  modalWord.className = `modal-word ${entry.type === 'wallon-francais' ? 'wallon-text' : 'francais-text'}`;
  
  modalBadge.textContent = entry.type === 'wallon-francais' ? 'Wallon → Français' : 'Français → Wallon';
  modalBadge.className = `badge ${entry.type === 'wallon-francais' ? 'badge-w2f' : 'badge-f2w'}`;
  
  modalDefinition.innerHTML = formatDefinitionText(entry);
  
  modalRefTome.innerHTML = `<i class="fa-solid fa-book-open"></i> Haust, Dictionnaire ${entry.type === 'wallon-francais' ? 'Liégeois (Tome II)' : 'Français-Liégeois (Tome III)'}`;
  modalRefPage.innerHTML = `<i class="fa-solid fa-file-lines"></i> Page ${entry.page}`;
  
  modalFavBtn.setAttribute('data-key', key);
  modalFavBtn.classList.toggle('active', isFav);
  
  detailModal.classList.add('active');
  
  const query = searchBox.value.trim();
  if (query.length >= 2) {
    saveHistory(query);
  }
}

function closeDetailModal() {
  detailModal.classList.remove('active');
  activeModalEntry = null;
}

// Event Listeners Configuration
function setupEventListeners() {
  let debounceTimeout;
  searchBox.addEventListener('input', () => {
    clearSearchBtn.style.display = searchBox.value.length > 0 ? 'block' : 'none';
    
    // Reset results expansion on a new search query!
    isExpanded = false;
    
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      performSearch();
    }, 200);
  });
  
  clearSearchBtn.addEventListener('click', () => {
    searchBox.value = '';
    clearSearchBtn.style.display = 'none';
    searchBox.focus();
    isExpanded = false;
    performSearch();
  });
  
  const tabs = [tabAll, tabW2F, tabF2W];
  tabs.forEach(tab => {
    tab.addEventListener('click', (e) => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentFilter = tab.getAttribute('data-filter');
      isExpanded = false; // Reset expand on tab toggle
      performSearch();
    });
  });
  
  closeModalBtn.addEventListener('click', closeDetailModal);
  detailModal.addEventListener('click', (e) => {
    if (e.target === detailModal) closeDetailModal();
  });
  
  modalFavBtn.addEventListener('click', () => {
    if (activeModalEntry) {
      toggleFavorite(activeModalEntry);
    }
  });
  
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && detailModal.classList.contains('active')) {
      closeDetailModal();
    }
  });
}

// Start Loading
init();
