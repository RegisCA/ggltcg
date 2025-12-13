---
applyTo: 'frontend/**/*.css'
description: "CSS design tokens and styling standards for GGLTCG frontend"
---

# CSS Design System

## Spacing Tokens

**CRITICAL**: All CSS spacing must use these design tokens.

```css
@theme {
  --spacing-component-xs: 8px;   /* Tight spacing within components */
  --spacing-component-sm: 12px;  /* Standard component padding */
  --spacing-component-md: 16px;  /* Default content spacing */
  --spacing-component-lg: 24px;  /* Section separation */
  --spacing-component-xl: 32px;  /* Major layout spacing */
}
```

## Utility Classes

Define and use these utility classes:

```css
.panel-padding {
  padding: var(--spacing-component-md);
}

.modal-padding {
  padding: var(--spacing-component-lg);
}

.card-padding {
  padding: var(--spacing-component-sm);
}

.content-spacing {
  gap: var(--spacing-component-md);
}
```

## Typography

**Single font family**: Lato (loaded via Google Fonts in `index.html`)

```css
body {
  font-family: 'Lato', sans-serif;
  font-weight: 400;
}
```

**Two weights only**:
- 400 (normal) - Body text
- 700 (bold) - Headings, titles, card names, emphasis

**NEVER** add custom font families. Visual hierarchy comes from weight and size.

## ✅ CORRECT Patterns

```css
.component {
  padding: var(--spacing-component-md);
  gap: var(--spacing-component-sm);
  font-weight: 700;
}

.section {
  margin-bottom: var(--spacing-component-lg);
}
```

## ❌ WRONG Patterns

```css
/* NEVER hardcode spacing */
.component {
  padding: 16px;  /* BAD! */
  gap: 12px;      /* BAD! */
  margin: 24px;   /* BAD! */
}

/* NEVER add custom fonts */
.card-name {
  font-family: 'Bangers', cursive;  /* BAD! */
}
```

## Exceptions

NONE. All spacing uses design tokens. All text uses Lato.
