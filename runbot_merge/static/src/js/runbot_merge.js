/* region light/dark selector */
function setColorScheme(t) {
    const classes = document.documentElement.classList;
    classes.remove('light', 'dark');

    const buttons = document.querySelectorAll('.theme-toggle button');
    for(const button of buttons) {
        button.classList.toggle(
            'active',
            (t === 'light' && button.classList.contains('fa-sun-o'))
            || (t === 'dark' && button.classList.contains('fa-moon-o'))
            || (t !== 'light' && t !== 'dark' && button.classList.contains('fa-ban'))
        );
    }

    switch (t) {
    case 'light': case 'dark':
        classes.add(t);
        window.localStorage.setItem('color-scheme', t);
        break;
    default:
        window.localStorage.removeItem('color-scheme');
    }
}

window.addEventListener("click", (e) => {
    const target = e.target;
    if (target.matches(".btn-group.theme-toggle button")) {
        setColorScheme(
            target.classList.contains('fa-sun-o') ? 'light' :
                target.classList.contains('fa-moon-o') ? 'dark' :
                    null
        );
    }
});

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", (e) => {
        setColorScheme(window.localStorage.getItem('color-scheme'));
    });
} else {
    setColorScheme(window.localStorage.getItem('color-scheme'));
}

/* endregion */

/* region cross-staging batch highlighting */
window.addEventListener("mouseover", (e) => {
    const batch = e.target.closest('li.batch');
    if (!batch) return;
    // Only trigger if coming from outside this batch
    const related = e.relatedTarget;
    if (!related || !batch.contains(related)) {
        for (const b of document.querySelectorAll(`li.batch[data-batch-id="${batch.dataset.batchId}"]`)) {
            b.style.outline = '1px dashed var(--body-color)';
        }
    }
});
window.addEventListener("mouseout", (e) => {
    const batch = e.target.closest('li.batch');
    if (!batch) return;
    // Only trigger if leaving to outside this batch
    const related = e.relatedTarget;
    if (!related || !batch.contains(related)) {
        for (const b of document.querySelectorAll(`li.batch[data-batch-id="${batch.dataset.batchId}"]`)) {
            b.style.outline = '';
        }
    }
});
/* endregion */

/* region dropdowns */
// If there's an open dropdown and we click outside the dropdown, close the dropdown.
window.addEventListener("click", e => {
    const dropdown = document.querySelector('details[name="dropdown"][open]');
    if (dropdown && !dropdown.contains(e.target)) {
        dropdown.removeAttribute('open');
    }
});

window.addEventListener("click", e => {
    const toggle = e.target.closest('a.dropdown-toggle');
    if (toggle) {
        toggle.classList.toggle('show');
    } else {
        const openToggle = document.querySelector('.dropdown-toggle.show');
        if (openToggle) {
            openToggle.classList.remove('show');
        }
    }
});

window.addEventListener("click", e => {
    const title = e.target.tagName !== 'A' && e.target.closest('section>section>h2');
    if (title) {
        title.classList.toggle('fold');
    }
});

/**
 * Only implement flipping up if there's no space below, not the left/right
 * toggling and sliding.
 *
 * TODO: use popper.js instead to get more flexible behaviour?
 */
function placeDropdown(details) {
    const viewportHeight = document.documentElement.clientHeight;

    const detailsRect = details.getBoundingClientRect();
    const dropDown = details.querySelector(':scope > div');
    const dropdownRect = dropDown.getBoundingClientRect()

    // Amount of clipping in each direction (negative if dropdown is fully inside the viewport)
    const clippingBottom = (detailsRect.bottom + dropdownRect.height) - viewportHeight;
    // fastpath
    if (clippingBottom <= 0 && !dropDown.style.inset) {
        return;
    }

    const clippingTop = -(detailsRect.top - dropdownRect.height);
    let inset;
    if (clippingBottom <= 0 || clippingBottom <= clippingTop) {
        inset = `${detailsRect.height}px auto auto 0`;
    } else {
        inset = `auto auto ${detailsRect.height}px 0`;
    }
    dropDown.style.inset = inset;
}

window.addEventListener("click", e => {
    const summary = e.target.closest('summary');
    const details = summary?.parentNode;
    if (details && !details.hasAttribute('open') && details.getAttribute('name') === 'dropdown') {
        summary.nextElementSibling.style.visibility = 'hidden';
    }
});
window.addEventListener("toggle", e => {
    if (e.newState === 'open' && e.target.matches('details[name="dropdown"]')) {
        placeDropdown(e.target);
    }
    e.target.querySelector(':scope>div').style.visibility = '';
}, {capture: true});

window.addEventListener('scroll', _ => {
    const openDetails = document.querySelector('details[name="dropdown"][open]');
    if (openDetails) {
        placeDropdown(openDetails);
    }
});
window.addEventListener('resize', _ => {
    const openDetails = document.querySelector('details[name="dropdown"][open]');
    if (openDetails) {
        placeDropdown(openDetails);
    }
});
/* endregion */