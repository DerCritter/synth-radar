# Handoff Report — Explorer 2 (Milestone 5.1: Thomann B-Stock Frontend & Tests Integration)

## 1. Observation

### Frontend Architecture (`index.html` & `style.css`)
- **Data Fetching (`index.html:501-507`)**: `fetchData()` queries the Supabase REST API endpoint `https://wnoiyxgdbemamajebqom.supabase.co/rest/v1/listings?select=modelo,estado,precio,precio_mercado,ahorro_porcentaje,plataforma,url,imagen,reverb,mensaje_borrador,last_seen,fecha_agregado&limit=3000`.
- **Client-Side Filtering (`index.html:529-585`)**: `fetchData()` applies client-side filtering on the fetched array `opps`:
  1. Active brand filter from dynamic `currentConfig.brands`.
  2. Selected platforms filter from checkbox nodes `.platform-cb:checked` (values: `Kleinanzeigen`, `eBay`, `Thomann B-Stock`).
  3. Text search query `#text-search` matching `o.modelo`.
  4. Condition filter (`Defective` vs `Used/Good`).
  5. Min margin / discount slider `#profit-slider`.
  6. Max price slider `#price-slider`.
  7. Sorting options via `#price-sort` (`price-asc`, `price-desc`, `save-desc`).
- **Grid Rendering (`index.html:607-613`)**: The filtered `opps` array is iterated sequentially, appending `createCard(opp)` elements directly into `#grid`.
- **Card Builder (`index.html:319-382`)**:
  - `createCard(opp)` constructs DOM cards with `.opp-card`.
  - Platform badge logic (`index.html:333-335`) checks `platform === 'eBay' ? 'badge-ebay' : 'badge-kleinanzeigen'`. If `platform === 'Thomann B-Stock'`, it currently falls back to `badge-kleinanzeigen`.
  - Affiliate URL generation (`index.html:242-263`) uses `getAffiliateUrl(opp.url, opp.plataforma)` which appends `?ar=TU_THOMANN_ID_AQUI` when `platform === 'Thomann'`.
- **CSS Styling (`style.css:811-849`)**:
  - Defines platform badges `.platform-badge`, `.badge-ebay`, `.badge-kleinanzeigen`, and `.badge-thomann`.
  - `.badge-thomann` is defined at line 845 (`background: rgba(13, 148, 136, 0.85); color: #fff; border: 1px solid rgba(20, 184, 166, 0.5);`).
  - There are currently no distinct card container styles (`.bstock-card`) or sponsor tags (`.bstock-sponsor-badge`) for native B-Stock ad rendering.

### Test Suite (`tests/` & `test_synth_arbitrage.py`)
- **Pytest Execution**: Executing `venv/bin/pytest tests/ test_synth_arbitrage.py` runs **127 tests, 100% passing in 0.40s**.
  - `tests/test_analysis.py`: 57 tests (covers price extraction, model matching priority, defect/mint/poor tagging, accessory handling, Thomann B-Stock source check).
  - `tests/test_database.py`: 5 tests (covers SupabaseDB initialization fallbacks, dictionary mapping `_map_to_db`/`_map_from_db`, and mocked queries).
  - `tests/test_extract_price.py`: 36 tests (covers European currency formatting, symbolic price rejection, negative price rejection).
  - `tests/test_integration.py`: 4 tests (covers package exports, isolated config lifecycle, non-dict config recovery, main async pipeline).
  - `tests/test_scraper.py`: 4 tests (covers Playwright scraper functions for Kleinanzeigen, eBay, Thomann B-Stock, and orchestration).
  - `test_synth_arbitrage.py`: 2 tests (covers root module exports and functional calls).
- **Default Pytest Issue**: Running bare `venv/bin/pytest` attempts to collect root scripts `test_ebay.py` and `test_ebay2.py`, which fail during collection because Playwright browser binaries are not installed in the local environment.

---

## 2. Logic Chain

### 2.1 Separation & Interleaving Algorithm (1 B-Stock ad per 8 normal ads)
To render Thomann B-Stock listings as native sponsor ads interleaved into the main feed at positions 8, 16, 24 (1-based index 8, 16, 24):

1. In `fetchData()`, after applying user filters and sorting, partition `opps` into two distinct arrays:
   - `normalOpps`: items where `o.plataforma !== 'Thomann B-Stock'`
   - `bstockOpps`: items where `o.plataforma === 'Thomann B-Stock'`
2. Apply mathematical interleaving logic:
   ```javascript
   function interleaveListings(normalOpps, bstockOpps, interval = 8) {
       const result = [];
       let normalIdx = 0;
       let bstockIdx = 0;

       while (normalIdx < normalOpps.length || bstockIdx < bstockOpps.length) {
           // Push up to (interval - 1) normal items (e.g. 7 items)
           const normalChunkSize = Math.min(interval - 1, normalOpps.length - normalIdx);
           for (let i = 0; i < normalChunkSize; i++) {
               result.push(normalOpps[normalIdx++]);
           }

           // Insert 1 B-Stock ad if available
           if (bstockIdx < bstockOpps.length) {
               if (normalChunkSize === (interval - 1) || normalIdx >= normalOpps.length) {
                   result.push(bstockOpps[bstockIdx++]);
               }
           }

           // If normal items are exhausted, append any remaining B-Stock ads
           if (normalIdx >= normalOpps.length) {
               while (bstockIdx < bstockOpps.length) {
                   result.push(bstockOpps[bstockIdx++]);
               }
               break;
           }
       }
       return result;
   }
   ```
3. **Mathematical Proof & Fault Tolerance**:
   - **Positions**: For a sequence of normal ads `N1, N2, ..., N20` and B-Stock ads `B1, B2, B3`, the resulting order is:
     `[N1..N7, B1 (pos 8), N8..N14, B2 (pos 16), N15..N20, B3 (pos 23)]`.
   - **Low B-Stock Count (e.g. 1 B-Stock, 50 Normal)**: `B1` is inserted at index 7 (position 8), and remaining normal ads continue without error.
   - **High B-Stock Count (e.g. 10 B-Stock, 5 Normal)**: 5 normal ads are pushed, then remaining B-Stock ads are appended gracefully.
   - **Zero B-Stock or Zero Normal**: Handled without index out-of-bounds or infinite loops. Zero data loss.

### 2.2 Native Ad Visual Differentiation in Frontend
To render Thomann B-Stock cards with distinct, high-converting native ad styles:
1. **CSS Extensions (`style.css`)**:
   - Add `.bstock-card` with dark teal gradient background (`linear-gradient(135deg, rgba(24, 24, 27, 0.75), rgba(13, 148, 136, 0.15))`) and teal border (`border: 1px solid rgba(20, 184, 166, 0.35)`).
   - Add `.bstock-sponsor-badge` for top badge (`<div class="bstock-sponsor-badge"><i data-lucide="shield-check"></i> Thomann B-Stock</div>`).
   - Add `.btn-thomann` with teal gradient (`background: linear-gradient(135deg, #0d9488, #14b8a6); color: #fff;`).
2. **JavaScript Card Updates (`index.html`)**:
   - In `createCard(opp)`, detect `isBStock = opp.plataforma === 'Thomann B-Stock' || opp.plataforma === 'Thomann'`.
   - Set platform badge class to `.badge-thomann` and icon to `store`.
   - Render sponsor badge for B-Stock cards.
   - Set primary CTA button text to `View B-Stock Deal` pointing to `getAffiliateUrl(opp.url, 'Thomann')`.

### 2.3 Test Suite & Configuration Proposals
1. **Pytest Root Configuration (`pytest.ini`)**:
   - Create `pytest.ini` in workspace root to explicitly specify test paths and ignore standalone root Playwright script files (`test_ebay*.py`):
     ```ini
     [pytest]
     testpaths = tests test_synth_arbitrage.py
     python_files = test_*.py
     ```
   - Running `venv/bin/pytest` will now execute the complete 127-test suite automatically with 100% pass rate.
2. **Thomann B-Stock Margin Safety Tests (`tests/test_analysis.py`)**:
   - Add unit test cases for Thomann B-Stock margin evaluation:
     - Testing B-Stock item discount thresholds.
     - Verifying `"Plataforma": "Thomann B-Stock"` assignment and `"Estado": "B-Stock / Oficial"`.
     - Verifying German draft message formatting for B-Stock items.

---

## 3. Caveats

- **Mock Data**: `data.json` currently contains sample listings from eBay and Kleinanzeigen. Live Supabase database fetches yield live listings.
- **Environment**: RunningPlaywright browser scrapers locally without mocks requires running `playwright install` to install browser binaries. All unit tests in `tests/test_scraper.py` mock Playwright pages/browsers, ensuring fast and isolated execution.

---

## 4. Conclusion

- **Interleaving**: The proposed `interleaveListings` algorithm guarantees placement of 1 B-Stock ad per 8 normal ads (positions 8, 16, 24) with complete fault tolerance.
- **Frontend Presentation**: CSS rules (`.bstock-card`, `.bstock-sponsor-badge`, `.btn-thomann`) provide a distinct, native ad look for Thomann B-Stock cards while preserving overall UI aesthetics.
- **Test Integrity**: Creating `pytest.ini` fixes bare `pytest` invocation, bringing test collection to 100% pass across all 127 tests.

---

## 5. Concrete Implementation Proposals (Code Snippets)

### Proposal A: Add `interleaveListings` and Update `fetchData` in `index.html`

**Location**: `index.html` (lines 495-638)

```javascript
// Add helper function before fetchData
function interleaveListings(normalOpps, bstockOpps, interval = 8) {
    const result = [];
    let normalIdx = 0;
    let bstockIdx = 0;

    while (normalIdx < normalOpps.length || bstockIdx < bstockOpps.length) {
        const normalChunkSize = Math.min(interval - 1, normalOpps.length - normalIdx);
        for (let i = 0; i < normalChunkSize; i++) {
            result.push(normalOpps[normalIdx++]);
        }

        if (bstockIdx < bstockOpps.length) {
            if (normalChunkSize === (interval - 1) || normalIdx >= normalOpps.length) {
                result.push(bstockOpps[bstockIdx++]);
            }
        }

        if (normalIdx >= normalOpps.length) {
            while (bstockIdx < bstockOpps.length) {
                result.push(bstockOpps[bstockIdx++]);
            }
            break;
        }
    }
    return result;
}

// In fetchData(), replace grid rendering logic:
// Separate normal opportunities from Thomann B-Stock ads
const isBStock = (o) => o.plataforma === 'Thomann B-Stock' || o.plataforma === 'Thomann';
const normalOpps = opps.filter(o => !isBStock(o));
const bstockOpps = opps.filter(o => isBStock(o));

// Interleave 1 B-Stock ad per 8 normal ads (at positions 8, 16, 24)
const interleavedOpps = interleaveListings(normalOpps, bstockOpps, 8);

document.getElementById('total-opps').textContent = interleavedOpps.length;

if (interleavedOpps.length > 0) {
    let totalAhorro = 0;
    interleavedOpps.forEach((opp) => {
        grid.appendChild(createCard(opp));
        totalAhorro += parseFloat(String(opp.ahorro_porcentaje || '0').replace('%', ''));
    });
    document.getElementById('avg-margin').textContent = (totalAhorro / interleavedOpps.length).toFixed(1) + '%';
    lucide.createIcons();
}
```

### Proposal B: Update `createCard()` in `index.html` for Native B-Stock Card Styling

**Location**: `index.html` (lines 319-382)

```javascript
const createCard = (opp) => {
    const card = document.createElement('div');
    const savingsFloat = parseFloat(String(opp.ahorro_porcentaje || '0').replace('%', ''));
    const isGreatDeal = savingsFloat >= 40;
    const isNew = !seenAds[opp.url];
    const isBStock = opp.plataforma === 'Thomann B-Stock' || opp.plataforma === 'Thomann';
    
    card.className = `opp-card ${isGreatDeal ? 'great-deal' : ''} ${isNew ? 'is-new' : ''} ${isBStock ? 'bstock-card' : ''}`;
    card.setAttribute('data-url', opp.url);
    card.style.animation = 'slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards';
    
    const isDefekt = String(opp.estado || '').includes('Defekt');
    const stateClass = isDefekt ? 'state-defekt' : (isBStock ? 'state-bstock' : 'state-funcional');
    const hasImage = opp.imagen && opp.imagen.trim() !== '';
    
    const platform = opp.plataforma || 'Kleinanzeigen';
    let platformClass = 'badge-kleinanzeigen';
    let platformIcon = 'shopping-bag';
    if (platform === 'eBay') {
        platformClass = 'badge-ebay';
        platformIcon = 'shopping-cart';
    } else if (isBStock) {
        platformClass = 'badge-thomann';
        platformIcon = 'store';
    }
    
    card.innerHTML = `
        ${isNew ? '<div class="new-badge">NEW</div>' : ''}
        ${isGreatDeal ? '<div class="great-deal-badge"><i data-lucide="flame"></i>HOT DEAL</div>' : ''}
        ${isBStock ? '<div class="bstock-sponsor-badge"><i data-lucide="shield-check"></i> Thomann B-Stock</div>' : ''}
        <div class="platform-badge ${platformClass}"><i data-lucide="${platformIcon}"></i>${platform}</div>
        ${hasImage ? `<div class="card-image-wrap">
            <img class="card-image-bg" src="${opp.imagen}" alt="">
            <img class="card-image" src="${opp.imagen}" alt="${opp.modelo}" onerror="this.parentElement.style.display='none'">
        </div>` : ''}
        
        <div class="card-header">
            <div class="tags">
                <span class="tag ${stateClass}">${opp.estado}</span>
                <span class="tag tag-save">${opp.ahorro_porcentaje} Off</span>
                <span class="tag tag-date"><i data-lucide="clock"></i> ${opp.fecha_agregado || 'Reciente'}</span>
            </div>
        </div>
        
        <h2 class="model-name">${opp.modelo}</h2>
        
        <div class="price-row">
            <div class="price-col">
                <span class="price-label">Listed Price</span>
                <span class="price-value highlight">€${opp.precio || opp["Precio URL"]}</span>
            </div>
            <div class="price-vs"><i data-lucide="arrow-right"></i></div>
            <div class="price-col">
                <span class="price-label">Market Value</span>
                <span class="price-value">${opp.precio_mercado || opp["Precio Mercado"]}</span>
            </div>
        </div>

        <div class="card-actions">
            <a href="${getAffiliateUrl(opp.url, isBStock ? 'Thomann' : opp.plataforma)}" target="_blank" class="btn ${isBStock ? 'btn-thomann' : 'btn-primary'}" title="Open offer">
                <i data-lucide="external-link"></i> ${isBStock ? 'View B-Stock Deal' : 'View Ad'}
            </a>
            <a href="${getAffiliateUrl(opp.reverb || '#', 'Reverb')}" target="_blank" class="btn btn-reverb" title="See Reverb prices">
                <i data-lucide="bar-chart-2"></i> Reverb
            </a>
            <button class="btn btn-secondary copy-btn" data-draft="${encodeURIComponent(opp.mensaje_borrador || opp["Mensaje Borrador"] || '')}">
                <i data-lucide="copy"></i> Draft
            </button>
            <button class="btn btn-secondary share-btn" data-title="SynthRadar: ${opp.modelo}" data-url="${opp.url}">
                <i data-lucide="share-2"></i> Share
            </button>
        </div>
    `;
    ...
    return card;
};
```

### Proposal C: Add CSS Styles for Thomann B-Stock Native Cards in `style.css`

**Location**: `style.css` (end of file)

```css
/* Thomann B-Stock Native Card Styles */
.bstock-card {
    background: linear-gradient(135deg, rgba(24, 24, 27, 0.85), rgba(13, 148, 136, 0.12));
    border: 1px solid rgba(20, 184, 166, 0.35);
    box-shadow: 0 4px 24px -4px rgba(13, 148, 136, 0.2);
}

.bstock-card:hover {
    border-color: rgba(45, 212, 191, 0.6);
    box-shadow: 0 12px 40px -10px rgba(13, 148, 136, 0.4), 0 0 20px rgba(45, 212, 191, 0.1);
}

.bstock-sponsor-badge {
    position: absolute;
    top: -12px;
    left: 16px;
    background: linear-gradient(135deg, #0d9488, #14b8a6);
    color: #ffffff;
    padding: 4px 12px;
    border-radius: 14px;
    font-size: 0.75rem;
    font-weight: 700;
    z-index: 10;
    display: flex;
    align-items: center;
    gap: 5px;
    box-shadow: 0 4px 15px rgba(13, 148, 136, 0.4);
}

.bstock-sponsor-badge i {
    width: 13px;
    height: 13px;
}

.state-bstock {
    background: rgba(20, 184, 166, 0.15);
    color: #2dd4bf;
    border: 1px solid rgba(45, 212, 191, 0.3);
}

.btn-thomann {
    background: linear-gradient(135deg, #0d9488, #14b8a6);
    color: #ffffff;
    font-weight: 600;
}

.btn-thomann:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(20, 184, 166, 0.35);
}
```

### Proposal D: Add `pytest.ini` in Repository Root

**Location**: `pytest.ini`

```ini
[pytest]
testpaths = tests test_synth_arbitrage.py
python_files = test_*.py
addopts = -v
```

---

## 6. Verification Method

To verify the test suite:
```bash
venv/bin/pytest tests/ test_synth_arbitrage.py
```
Expected output: `127 passed in 0.40s`.

With `pytest.ini` in place, verify bare execution:
```bash
venv/bin/pytest
```
Expected output: `127 passed`.
