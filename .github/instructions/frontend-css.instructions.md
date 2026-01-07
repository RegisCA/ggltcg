---
applyTo: 'frontend/**/*.css'
description: "CSS design tokens and styling standards for GGLTCG frontend"
---

# CSS Design System

**Full details**: See `frontend/AGENTS.md` for comprehensive frontend patterns.

## Spacing Tokens

**CRITICAL**: All CSS spacing must use these design tokens.

```css
@theme {
  --spacing-component-xs: 8px;   /* Tight spacing */
  --spacing-component-sm: 12px;  /* Component padding */
  --spacing-component-md: 16px;  /* Default spacing */
  --spacing-component-lg: 24px;  /* Section separation */
  --spacing-component-xl: 32px;  /* Major layout */
}
```

## Utility Classes

```css
.panel-padding   { padding: var(--spacing-component-md); }
.modal-padding   { padding: var(--spacing-component-lg); }
.card-padding    { padding: var(--spacing-component-sm); }
.content-spacing { gap: var(--spacing-component-md); }
```

## Typography

**Single font**: Lato (Google Fonts). **Two weights only**: 400, 700.

```css
body {
  font-family: 'Lato', sans-serif;
  font-weight: 400;
}
```

## ✅ CORRECT

```css
.component {
  padding: var(--spacing-component-md);
  gap: var(--spacing-component-sm);
  font-weight: 700;
}
```

## ❌ WRONG

```css
/* NEVER hardcode spacing */
.component {
  padding: 16px;  /* BAD! */
  gap: 12px;      /* BAD! */
}

/* NEVER add custom fonts */
.card-name {
  font-family: 'Bangers', cursive;  /* BAD! */
}
```

**Exceptions**: NONE. All spacing uses tokens. All text uses Lato.
