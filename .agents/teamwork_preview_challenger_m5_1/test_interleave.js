// Empirical stress test harness for interleaveListings function in index.html

function interleaveListings(normalOpps, bstockOpps, interval = 8) {
    if (!bstockOpps || bstockOpps.length === 0) return normalOpps || [];
    if (!normalOpps || normalOpps.length === 0) return bstockOpps || [];

    const result = [];
    let bIndex = 0;

    for (let i = 0; i < normalOpps.length; i++) {
        result.push(normalOpps[i]);
        if ((i + 1) % interval === 0 && bIndex < bstockOpps.length) {
            result.push(bstockOpps[bIndex++]);
        }
    }

    while (bIndex < bstockOpps.length) {
        result.push(bstockOpps[bIndex++]);
    }

    return result;
}

// Helper to generate items
function makeNormal(count) {
    return Array.from({ length: count }, (_, i) => ({ id: `N${i + 1}`, type: 'normal' }));
}

function makeBStock(count) {
    return Array.from({ length: count }, (_, i) => ({ id: `B${i + 1}`, type: 'bstock' }));
}

function runTestCase(name, normalCount, bstockCount, customNormal = null, customBStock = null) {
    const normal = customNormal !== null ? customNormal : makeNormal(normalCount);
    const bstock = customBStock !== null ? customBStock : makeBStock(bstockCount);

    const result = interleaveListings(normal, bstock);

    const normalInResult = result.filter(x => x && x.type === 'normal');
    const bstockInResult = result.filter(x => x && x.type === 'bstock');

    // Find 1-based positions of all B-Stock items in result
    const bstockPositions = [];
    result.forEach((item, index) => {
        if (item && item.type === 'bstock') {
            bstockPositions.push({
                id: item.id,
                zeroBasedIndex: index,
                oneBasedPosition: index + 1
            });
        }
    });

    // Integrity checks
    const totalInputCount = (normal ? normal.length : 0) + (bstock ? bstock.length : 0);
    const totalOutputCount = result.length;

    const normalDropped = (normal ? normal.length : 0) - normalInResult.length;
    const bstockDropped = (bstock ? bstock.length : 0) - bstockInResult.length;

    // Duplication check
    const seenIds = new Set();
    let duplicates = 0;
    result.forEach(item => {
        if (item && item.id) {
            if (seenIds.has(item.id)) duplicates++;
            seenIds.add(item.id);
        }
    });

    // Check relative ordering of normal items
    let normalOrderIntact = true;
    let nIdx = 0;
    for (const item of result) {
        if (item && item.type === 'normal') {
            if (item.id !== normal[nIdx].id) {
                normalOrderIntact = false;
                break;
            }
            nIdx++;
        }
    }

    return {
        name,
        inputNormalCount: normal ? normal.length : 0,
        inputBStockCount: bstock ? bstock.length : 0,
        totalOutputCount,
        normalInResultCount: normalInResult.length,
        bstockInResultCount: bstockInResult.length,
        normalDropped,
        bstockDropped,
        duplicates,
        normalOrderIntact,
        bstockPositions,
        fullSequence: result.map(x => x.id)
    };
}

console.log("=== EMPIRICAL STRESS TESTS FOR interleaveListings ===\n");

const testCases = [
    { name: "Edge Case 1: 0 normal / 0 B-Stock", n: 0, b: 0 },
    { name: "Edge Case 2: 1 normal / 100 B-Stock", n: 1, b: 100 },
    { name: "Edge Case 3: 100 normal / 0 B-Stock", n: 100, b: 0 },
    { name: "Edge Case 4: Exactly 7 normal / 1 B-Stock", n: 7, b: 1 },
    { name: "Edge Case 5: 16 normal / 2 B-Stock", n: 16, b: 2 },
    { name: "Boundary: 8 normal / 1 B-Stock", n: 8, b: 1 },
    { name: "Boundary: 15 normal / 2 B-Stock", n: 15, b: 2 },
    { name: "Boundary: 24 normal / 3 B-Stock", n: 24, b: 3 },
    { name: "Boundary: Null / Undefined handling", customN: null, customB: null },
];

testCases.forEach(tc => {
    let res;
    if (tc.customN !== undefined || tc.customB !== undefined) {
        res = runTestCase(tc.name, 0, 0, tc.customN, tc.customB);
    } else {
        res = runTestCase(tc.name, tc.n, tc.b);
    }
    console.log(`--- ${res.name} ---`);
    console.log(`Inputs: Normal=${res.inputNormalCount}, B-Stock=${res.inputBStockCount}`);
    console.log(`Output Total: ${res.totalOutputCount} (Normal=${res.normalInResultCount}, B-Stock=${res.bstockInResultCount})`);
    console.log(`Integrity: Normal Dropped=${res.normalDropped}, B-Stock Dropped=${res.bstockDropped}, Duplicates=${res.duplicates}, Normal Order Intact=${res.normalOrderIntact}`);
    console.log(`B-Stock Placement Positions (1-based):`, res.bstockPositions.map(p => `${p.id}@pos${p.oneBasedPosition}(idx${p.zeroBasedIndex})`).join(', ') || 'None');
    if (res.totalOutputCount <= 25) {
        console.log(`Sequence: ${res.fullSequence.join(', ')}`);
    } else {
        console.log(`Sequence (first 25): ${res.fullSequence.slice(0, 25).join(', ')}...`);
    }
    console.log("\n");
});
