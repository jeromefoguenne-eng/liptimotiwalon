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
  return `${entry.word}_T${entry.tome}_P${entry.page}_${entry.type}`;
}

// Initialize Application
async function init() {
  try {
    const response = await fetch('dico.json');
    if (!response.ok) throw new Error("Impossible de charger dico.json");
    
    dictionary = await response.json();
    
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
    label.textContent = entry.word;
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
  
  container.innerHTML = `
    <div class="mot-word" id="mot-du-jour-word">${mot.word}</div>
    <div class="badge ${mot.type === 'wallon-francais' ? 'badge-w2f' : 'badge-f2w'}" style="margin-left: 0.75rem; vertical-align: middle; display: inline-block;">
      ${mot.type === 'wallon-francais' ? 'Wallon' : 'Français'}
    </div>
    <div class="mot-definition" style="margin-top: 0.5rem;">
      ${formatDefinitionText(mot.definition, mot.word, mot.type)}
    </div>
  `;
  
  document.getElementById('mot-du-jour-word').addEventListener('click', () => openDetailModal(mot));
}

// Parse custom characters and separate French and Wallon visually
function formatDefinitionText(definition, word, type) {
  if (!definition) return '';
  
  // Format the headword inside definitions
  const headwordHtml = type === 'wallon-francais' 
    ? `<strong class="wallon-text">${word}</strong>` 
    : `<strong class="francais-text">${word}</strong>`;
  
  let formatted = definition.replace(/~/g, headwordHtml);
  
  // Distinguish French and Wallon:
  if (type === 'wallon-francais') {
    // Tome 2: "v. tr., emménager: dj'abague pô a pô..."
    // We split by ':' to separate French translation from Wallon examples.
    const colonIndex = formatted.indexOf(':');
    if (colonIndex !== -1) {
      const frenchPart = formatted.substring(0, colonIndex + 1);
      const wallonPart = formatted.substring(colonIndex + 1);
      formatted = `<span class="french-def-part">${frenchPart}</span><span class="wallon-examples-part">${wallonPart}</span>`;
    }
  } else {
    // Tome 3: Français -> Wallon
    // We style the main definitions as Wallon text (serif/italic), except metadata in brackets/parens.
    formatted = `<span class="wallon-examples-part">${formatted}</span>`;
  }
  
  // Format sub-entries (preceded by '|')
  formatted = formatted.replace(/\|\s*([^,;:|]+)/g, (match, subWord) => {
    return `<span class="sub-entry-block"><strong class="wallon-sub-title"><i class="fa-solid fa-share-nodes" style="font-size: 0.8rem; margin-right: 0.4rem; opacity: 0.7;"></i> ${subWord.trim()}</strong></span>`;
  });
  
  // Mute parens and brackets
  formatted = formatted.replace(/(\([^)]+\))/g, '<span class="muted-parens">$1</span>');
  formatted = formatted.replace(/(\[[^\]]+\])/g, '<span class="muted-parens">$1</span>');
  
  return formatted;
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
    filteredResults.sort((a, b) => a.word.localeCompare(b.word));
    resultsLabel.textContent = currentFilter === 'all' ? "Toutes les entrées" : (currentFilter === 'wallon-francais' ? "Entrées Wallon-Français" : "Entrées Français-Wallon");
  } else {
    const scored = [];
    
    for (let i = 0; i < dictionary.length; i++) {
      const entry = dictionary[i];
      
      if (currentFilter !== 'all' && entry.type !== currentFilter) continue;
      
      const normWord = removeAccents(entry.word);
      const normDef = removeAccents(entry.definition);
      
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
      if (a.entry.word.length !== b.entry.word.length) return a.entry.word.length - b.entry.word.length;
      return a.entry.word.localeCompare(b.entry.word);
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
    
    card.innerHTML = `
      <div class="card-top">
        <span class="card-word ${wordClass}">${entry.word}</span>
        <span class="badge ${entry.type === 'wallon-francais' ? 'badge-w2f' : 'badge-f2w'}">
          ${entry.type === 'wallon-francais' ? 'Wallon' : 'Français'}
        </span>
      </div>
      <p class="card-definition">${formatDefinitionText(entry.definition, entry.word, entry.type)}</p>
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
let activeModalEntry = null;

function openDetailModal(entry) {
  activeModalEntry = entry;
  const key = getEntryKey(entry);
  const isFav = favorites.has(key);
  
  modalWord.textContent = entry.word;
  modalWord.className = `modal-word ${entry.type === 'wallon-francais' ? 'wallon-text' : 'francais-text'}`;
  
  modalBadge.textContent = entry.type === 'wallon-francais' ? 'Wallon → Français' : 'Français → Wallon';
  modalBadge.className = `badge ${entry.type === 'wallon-francais' ? 'badge-w2f' : 'badge-f2w'}`;
  
  modalDefinition.innerHTML = formatDefinitionText(entry.definition, entry.word, entry.type);
  
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
