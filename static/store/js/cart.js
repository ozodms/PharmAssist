const updateBtns = document.querySelectorAll('.update-cart');

async function postUpdate(productId, action) {
    const resp = await fetch('/update_item/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.csrftoken,
        },
        body: JSON.stringify({ productId, action })
    });

    if (resp.ok) {
        location.reload();
    } else {
        console.error('Update failed', await resp.text());
    }
}


document.querySelectorAll('.remove-item').forEach(btn => {
    btn.addEventListener('click', async () => {
        const pid = btn.dataset.product;
        try {
            const resp = await fetch('/update_item/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrftoken,
                },
                body: JSON.stringify({ productId: pid, action: 'clear' })
            });
            if (resp.ok) {
                location.reload();
            } else {
                console.error('Remove failed', await resp.text());
            }
        } catch (e) {
            console.error('Remove error', e);
        }
    });
});


for (const btn of updateBtns) {
    btn.addEventListener('click', () => {
        const productId = btn.dataset.product;
        const action = btn.dataset.action;

        if (window.USER === 'AnonymousUser') {
            postUpdate(productId, action);
        } else {
            postUpdate(productId, action);
        }
    });
}



function getToken(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
function clamp(val, min, max) { return Math.max(min, Math.min(max, val)); }


function formatMoney(num) {
    const n = Number(num);
    return isFinite(n) ? n.toFixed(2) : '0.00';
}

function recalcForProduct(pid) {
    const qtyInput = document.querySelector(`.qty-input[data-product="${pid}"]`);
    const priceEl = qtyInput?.closest('.sm\\:col-span-3')?.querySelector('.unit-price');
    const subtotalEl = document.querySelector(`.item-subtotal[data-product="${pid}"]`);

    if (!qtyInput || !priceEl || !subtotalEl) return;

    const qty = parseInt(qtyInput.value || qtyInput.min || '1', 10);
    const price = parseFloat(priceEl.dataset.price || priceEl.textContent || '0');

    const subtotal = qty * price;
    subtotalEl.textContent = formatMoney(subtotal);
}

function recalcTotals() {
    let total = 0;
    let count = 0;

    document.querySelectorAll('.qty-input').forEach(input => {
        const qty = parseInt(input.value || input.min || '1', 10);
        const priceEl = input.closest('.sm\\:col-span-3')?.querySelector('.unit-price');
        const price = parseFloat(priceEl?.dataset.price || priceEl?.textContent || '0');

        count += isFinite(qty) ? qty : 0;
        total += (isFinite(qty) && isFinite(price)) ? qty * price : 0;
    });

    const totalAmountEl = document.getElementById('total-amount');
    const totalItemsEl = document.getElementById('total-items');

    if (totalAmountEl) totalAmountEl.textContent = formatMoney(total);
    if (totalItemsEl) totalItemsEl.textContent = count;
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.qty-input').forEach(input => {
        input.addEventListener('input', () => {
            const min = parseInt(input.min) || 1;
            const max = parseInt(input.max) || 999999;
            let v = parseInt(input.value, 10);
            if (isNaN(v)) v = min;
            if (v < min) v = min;
            if (v > max) v = max;
            input.value = v;

            const pid = input.dataset.product;
            recalcForProduct(pid);
            recalcTotals();
        });
    });

    document.querySelectorAll('.qty-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const pid = btn.dataset.product;
            const delta = parseInt(btn.dataset.delta, 10);
            const input = document.querySelector(`.qty-input[data-product="${pid}"]`);
            if (!input) return;

            const min = parseInt(input.min) || 1;
            const max = parseInt(input.max) || 999999;
            let v = parseInt(input.value || min, 10);
            v = isNaN(v) ? min : v;
            v = Math.max(min, Math.min(max, v + delta));
            input.value = v;

            recalcForProduct(pid);
            recalcTotals();
        });
    });

    recalcTotals();
});

document.querySelectorAll('.remove-item').forEach(btn => {
    btn.addEventListener('click', async () => {
        const pid = btn.dataset.product;
        try {
            const resp = await fetch('/update_item/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrftoken,
                },
                body: JSON.stringify({ productId: pid, action: 'clear' })
            });
            if (resp.ok) {
                location.reload();
            } else {
                console.error('Remove failed', await resp.text());
            }
        } catch (e) {
            console.error('Remove error', e);
        }
    });
});
