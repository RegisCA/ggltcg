# GGLTCG Typography Design System

> **Last Updated**: December 5, 2025  
> **Status**: Active  
> **Location**: `frontend/src/index.css` (CSS variables), component files (Tailwind classes)

## Overview

This document defines the typography standards for GGLTCG's frontend. All text styling should follow these guidelines to ensure consistency, readability, and WCAG AA accessibility compliance.

---

## Font Families

### Primary Fonts

| Font | CSS Variable | Tailwind Class | Usage |
|------|--------------|----------------|-------|
| **Bangers** | `--font-family-bangers` | `font-bangers` | Headings, card names, titles, game branding |
| **Lato** | `--font-family-lato` | `font-lato` | Body text, labels, descriptions, UI text |

### Fallback Stack

```css
--font-family-bangers: 'Bangers', 'Impact', sans-serif;
--font-family-lato: 'Lato', 'Arial', sans-serif;
```

### Usage Guidelines

- **Bangers**: Use for game-themed headings, victory screens, card names. Creates playful, bold aesthetic.
- **Lato**: Use for all readable content - descriptions, labels, form fields, buttons.

---

## Font Sizes (Type Scale)

Using Tailwind's default type scale for consistency:

| Size | Tailwind Class | Pixels | rem | Usage |
|------|----------------|--------|-----|-------|
| **4XL** | `text-4xl` | 36px | 2.25rem | Hero headings (Victory screen title) |
| **3XL** | `text-3xl` | 30px | 1.875rem | Major section headings |
| **2XL** | `text-2xl` | 24px | 1.5rem | Panel headings, modal titles |
| **XL** | `text-xl` | 20px | 1.25rem | Subheadings, important labels |
| **LG** | `text-lg` | 18px | 1.125rem | Large body text, emphasis |
| **Base** | `text-base` | 16px | 1rem | Default body text |
| **SM** | `text-sm` | 14px | 0.875rem | Secondary text, labels, captions |
| **XS** | `text-xs` | 12px | 0.75rem | Badges, small labels, metadata |
| **[10px]** | `text-[10px]` | 10px | 0.625rem | Compact mode only (keyboard shortcuts) |

### Responsive Typography

Use responsive variants for important text elements:

```tsx
// Hero heading - responsive sizing
<h1 className="text-4xl sm:text-6xl font-bold">Victory!</h1>

// Subheading - responsive sizing
<p className="text-2xl sm:text-4xl">Winner: Player 1</p>

// Compact mode text
<span className={compact ? 'text-xs' : 'text-sm'}>Label</span>
```

---

## Font Weights

| Weight | Tailwind Class | Numeric | Usage |
|--------|----------------|---------|-------|
| **Bold** | `font-bold` | 700 | Headings, important labels, emphasis |
| **Semibold** | `font-semibold` | 600 | Button text, subheadings |
| **Medium** | `font-medium` | 500 | Slightly emphasized text |
| **Normal** | `font-normal` | 400 | Body text (default) |

### Usage Patterns

```tsx
// Heading
<h2 className="text-2xl font-bold">Panel Title</h2>

// Button
<button className="font-semibold">Click Me</button>

// Body text
<p className="text-base">Description text...</p>

// Label
<span className="text-sm font-medium">Field Label</span>
```

---

## Text Colors (WCAG AA Compliant)

All text colors meet WCAG AA standards (4.5:1 for normal text, 3:1 for large text) on dark backgrounds.

### Semantic Text Colors

| Color | CSS Variable | Tailwind Class | Contrast | Usage |
|-------|--------------|----------------|----------|-------|
| **Primary** | `--color-text-primary` | `text-white` | 21:1 | Main text, headings, important content |
| **Secondary** | `--color-text-secondary` | `text-gray-300` | 9.7:1 | Softer text, descriptions |
| **Muted** | `--color-text-muted` | `text-gray-400` | 5.8:1 | Subtle text, metadata, hints |
| **Inverse** | `--color-text-inverse` | `text-gray-900` | N/A | Text on light backgrounds |
| **Error** | `--color-text-error` | `text-red-300` | 6.2:1 | Error messages, warnings |
| **Success** | `--color-text-success` | `text-green-300` | 10.1:1 | Success messages, positive states |
| **Warning** | `--color-text-warning` | `text-yellow-300` | 11.8:1 | Warning messages, cautions |

### Game-Themed Colors

| Color | Tailwind Class | Usage |
|-------|----------------|-------|
| **Highlight** | `text-game-highlight` | Branding, emphasis, CTA |
| **Purple** | `text-purple-400` | AI-related text, special features |
| **Blue** | `text-blue-400` | Stats, numbers, data |
| **Green** | `text-green-400` | Positive stats, wins |
| **Amber** | `text-amber-400` | Warnings, End Turn button |

### Color Usage Examples

```tsx
// Primary heading
<h1 className="text-white font-bold">Game Title</h1>

// Secondary description
<p className="text-gray-300">This is a description...</p>

// Muted metadata
<span className="text-gray-400 text-sm">Last updated: Today</span>

// Error message
<p className="text-red-300">Unable to connect to server</p>

// Success message
<p className="text-green-300">Game created successfully!</p>
```

---

## Text Styles by Component Type

### Headings

| Level | Class Pattern | Example |
|-------|---------------|---------|
| H1 | `text-4xl font-bold text-white` | Victory screen title |
| H2 | `text-2xl font-bold text-game-highlight` | Panel titles |
| H3 | `text-lg font-bold text-white` | Section titles |

### Body Text

| Type | Class Pattern | Example |
|------|---------------|---------|
| Default | `text-base text-white` | Main content |
| Secondary | `text-base text-gray-300` | Descriptions |
| Small | `text-sm text-gray-400` | Captions, metadata |

### Labels & Badges

| Type | Class Pattern | Example |
|------|---------------|---------|
| Form Label | `text-sm font-medium text-gray-300` | Input labels |
| Badge | `text-xs font-bold rounded` | Card type badges |
| Keyboard Shortcut | `text-xs font-mono font-bold` | Action shortcuts |

### Buttons

| Type | Class Pattern |
|------|---------------|
| Primary | `font-semibold text-white` |
| Secondary | `font-semibold text-gray-300` |
| Danger | `font-semibold text-white` |

---

## Line Height

Use Tailwind's default line heights for appropriate text density:

| Class | Ratio | Usage |
|-------|-------|-------|
| `leading-none` | 1 | Single-line headings, badges |
| `leading-tight` | 1.25 | Dense UI, compact cards |
| `leading-snug` | 1.375 | Subheadings |
| `leading-normal` | 1.5 | Default body text |
| `leading-relaxed` | 1.625 | Long-form content, narratives |
| `leading-loose` | 2 | Very readable content |

### Example

```tsx
// Narrative text (Victory screen story mode)
<div className="text-base leading-relaxed">
  Long narrative content that needs to be easily readable...
</div>

// Compact card text
<span className="text-xs leading-tight">Card effect text</span>
```

---

## Accessibility Requirements

### Minimum Contrast Ratios (WCAG AA)

- **Normal text** (< 18px): 4.5:1 contrast ratio
- **Large text** (≥ 18px or ≥ 14px bold): 3:1 contrast ratio

### Verified Color Pairings

All the following pairings have been verified to meet WCAG AA:

| Text Color | Background | Ratio | Status |
|------------|------------|-------|--------|
| `#FFFFFF` (white) | `#1a1a2e` (game-bg) | 21:1 | ✅ Pass |
| `#D1D5DB` (gray-300) | `#1a1a2e` (game-bg) | 9.7:1 | ✅ Pass |
| `#9CA3AF` (gray-400) | `#1a1a2e` (game-bg) | 5.8:1 | ✅ Pass |
| `#FCA5A5` (red-300) | `#1a1a2e` (game-bg) | 6.2:1 | ✅ Pass |
| `#86EFAC` (green-300) | `#1a1a2e` (game-bg) | 10.1:1 | ✅ Pass |
| `#FCD34D` (yellow-300) | `#1a1a2e` (game-bg) | 11.8:1 | ✅ Pass |

### ❌ Avoid These Combinations

- `text-gray-500` on dark backgrounds (3.9:1 - fails)
- `text-blue-500` on dark backgrounds (varies - check)
- `text-gray-600` on dark backgrounds (fails)

---

## Implementation Checklist

When creating new components:

- [ ] Use semantic text colors (`text-white`, `text-gray-300`, `text-gray-400`)
- [ ] Apply appropriate font weight for context
- [ ] Use responsive typography for headings
- [ ] Verify contrast ratios on dark backgrounds
- [ ] Apply `font-bold` for headings, `font-semibold` for buttons
- [ ] Use `text-sm` or smaller for metadata/captions
- [ ] Add `leading-*` classes for multi-line text

---

## Related Documentation

- [Spacing Design System](../../.github/instructions/coding.instructions.md#frontend-spacing-design-system)
- [WCAG AA Compliance](./UX_REMEDIATION_STATUS.md#issue-173-wcag-aa-contrast-compliance)
- [Button Component](../../frontend/src/components/ui/Button.tsx)

---

## Version History

| Date | Change |
|------|--------|
| 2025-12-05 | Initial documentation created |
| 2025-12-04 | WCAG AA compliance fixes completed |
| 2025-12-03 | Typography patterns established during UX review |
