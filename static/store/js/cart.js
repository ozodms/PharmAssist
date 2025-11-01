const CSRF = window.csrftoken || (document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? '');

async function postUpdate(productId, action, opts = {}) {
    const resp = await fetch('/update_item/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CSRF,
        },
        body: JSON.stringify({ productId, action })
    });

    if (!resp.ok) {
        console.error('Update failed', await resp.text());
        return;
    }

    if (opts.reload === false) {
        return;
    }

    const hasTotals = document.getElementById('total-amount');
    if (!hasTotals) {
        location.reload();
    } else {
        recalcTotals();
    }
}

function formatMoney(num) {
    const n = Number(num);
    return isFinite(n) ? n.toFixed(2) : '0.00';
}

function recalcForProduct(pid) {
    const qtyInput = document.querySelector(`.qty-input[data-product="${pid}"]`);
    if (!qtyInput) return;

    const row = qtyInput.closest('[data-cart-row]');
    if (!row) return;

    const priceEl = row.querySelector('.unit-price');
    const subtotalEl = row.querySelector(`.item-subtotal[data-product="${pid}"]`);
    if (!priceEl || !subtotalEl) return;

    const qty = parseInt(qtyInput.value || qtyInput.min || '1', 10);
    const price = parseFloat(priceEl.dataset.price || priceEl.textContent || '0');

    subtotalEl.textContent = formatMoney(qty * price);
}

function recalcTotals() {
    let total = 0;
    let count = 0;

    document.querySelectorAll('.qty-input').forEach(input => {
        const row = input.closest('[data-cart-row]');
        const priceEl = row ? row.querySelector('.unit-price') : null;
        const qty = parseInt(input.value || input.min || '1', 10);
        const price = parseFloat(priceEl?.dataset.price || priceEl?.textContent || '0');

        if (isFinite(qty)) count += qty;
        if (isFinite(qty) && isFinite(price)) total += qty * price;
    });

    const totalAmountEl = document.getElementById('total-amount');
    const totalItemsEl = document.getElementById('total-items');

    if (totalAmountEl) totalAmountEl.textContent = formatMoney(total);
    if (totalItemsEl) totalItemsEl.textContent = count;
}


function applyQtyToInput(input, nextVal) {
    const min = parseInt(input.min) || 1;
    const max = parseInt(input.max) || 999999;
    let v = parseInt(nextVal, 10);

    if (isNaN(v)) v = min;
    if (v < min) v = min;
    if (v > max) v = max;

    input.value = v;

    const pid = input.dataset.product;
    recalcForProduct(pid);
    recalcTotals();
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.update-cart').forEach(btn => {
        btn.addEventListener('click', () => {
            const productId = btn.dataset.product;
            const action = btn.dataset.action || 'add';
            postUpdate(productId, action);
        });
    });

    document.querySelectorAll('.remove-item').forEach(btn => {
        btn.addEventListener('click', async () => {
            const pid = btn.dataset.product;
            const row = btn.closest('[data-cart-row]');

            await postUpdate(pid, 'clear', { reload: false });
            if (row) {
                row.remove();
            }
            recalcTotals();
        });
    });

    document.querySelectorAll('.qty-input').forEach(input => {
        input.addEventListener('input', () => {
            applyQtyToInput(input, input.value);
        });
    });

    document.querySelectorAll('.qty-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const pid = btn.dataset.product;
            const input = document.querySelector(`.qty-input[data-product="${pid}"]`);
            if (!input) return;
            const delta = parseInt(btn.dataset.delta, 10) || 0;
            const current = parseInt(input.value, 10) || parseInt(input.min) || 1;
            applyQtyToInput(input, current + delta);
        });
    });

    const checkoutLink = document.getElementById('checkout-go');
    if (checkoutLink) {
        checkoutLink.addEventListener('click', async (e) => {
            e.preventDefault();
            const inputs = document.querySelectorAll('.qty-input');
            const reqs = [];
            inputs.forEach(input => {
                const pid = input.dataset.product;
                const qty = parseInt(input.value || input.min || '1', 10);
                reqs.push(
                    fetch(`/set_qty/${pid}/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': CSRF,
                            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                        },
                        body: new URLSearchParams({ quantity: qty })
                    })
                );
            });
            try {
                await Promise.all(reqs);
            } catch (err) {
                console.error('sync before checkout failed', err);
            }
            window.location.href = checkoutLink.getAttribute('href');
        });
    }

    recalcTotals();
});
