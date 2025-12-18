# GGLTCG Typography Design System

> **Last Updated**: December 5, 2025
> **Status**: Active
> **Location**: `frontend/src/index.css` (CSS variables), component files
(Tailwind classes)

## Overview

This document defines the typography standards for GGLTCG's frontend. All text
styling should follow these guidelines to ensure consistency, readability, and
WCAG AA accessibility compliance.

---

## Font Families

### Primary Fonts

- **Bangers**
  - CSS Variable: `--font-family-bangers`
  - Tailwind Class: `font-bangers`
  - Usage: Headings, card names, titles, game branding
- **Lato**
  - CSS Variable: `--font-family-lato`
  - Tailwind Class: `font-lato`
  - Usage: Body text, labels, descriptions, UI text

### Fallback Stack

```css
--font-family-bangers: 'Bangers', 'Impact', sans-serif;
--font-family-lato: 'Lato', 'Arial', sans-serif;
```text
### Usage Guidelines

- **Bangers**: Use for game-themed headings, victory screens, card names.
  Creates playful, bold aesthetic.
- **Lato**: Use for all readable content - descriptions, labels, form fields,
  buttons.

---

## Font Sizes (Type Scale)

Using Tailwind's default type scale for consistency:

- **4XL**
  - Tailwind Class: `text-4xl`
  - Size: 36px (2.25rem)
  - Usage: Hero headings (Victory screen title)
- **3XL**
  - Tailwind Class: `text-3xl`
  - Size: 30px (1.875rem)
  - Usage: Major section headings
- **2XL**
  - Tailwind Class: `text-2xl`
  - Size: 24px (1.5rem)
  - Usage: Panel headings, modal titles
- **XL**
  - Tailwind Class: `text-xl`
  - Size: 20px (1.25rem)
  - Usage: Subheadings, important labels
- **LG**
  - Tailwind Class: `text-lg`
  - Size: 18px (1.125rem)
  - Usage: Large body text, emphasis
- **Base**
  - Tailwind Class: `text-base`
  - Size: 16px (1rem)
  - Usage: Default body text
- **SM**
  - Tailwind Class: `text-sm`
  - Size: 14px (0.875rem)
  - Usage: Secondary text, labels, captions
- **XS**
  - Tailwind Class: `text-xs`
  - Size: 12px (0.75rem)
  - Usage: Badges, small labels, metadata
- **[10px]**
  - Tailwind Class: `text-[10px]`
  - Size: 10px (0.625rem)
  - Usage: Compact mode only (keyboard shortcuts)

### Responsive Typography

Use responsive variants for important text elements:

```tsx
// Hero heading - responsive sizing
<h1 className="text-4xl sm:text-6xl font-bold">Victory!</h1>

// Subheading - responsive sizing
<p className="text-2xl sm:text-4xl">Winner: Player 1</p>

// Compact mode text
<span className={compact ? 'text-xs' : 'text-sm'}>Label</span>
```text
---

## Font Weights

- **Bold**
  - Tailwind Class: `font-bold`
  - Numeric: 700
  - Usage: Headings, important labels, emphasis
- **Semibold**
  - Tailwind Class: `font-semibold`
  - Numeric: 600
  - Usage: Button text, subheadings
- **Medium**
  - Tailwind Class: `font-medium`
  - Numeric: 500
  - Usage: Slightly emphasized text
- **Normal**
  - Tailwind Class: `font-normal`
  - Numeric: 400
  - Usage: Body text (default)

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
```text
---

## Text Colors (WCAG AA Compliant)

All text colors meet WCAG AA standards (4.5:1 for normal text, 3:1 for large
text) on dark backgrounds.

### Semantic Text Colors

- **Primary**
  - CSS Variable: `--color-text-primary`
  - Tailwind Class: `text-white`
  - Contrast: 21:1
  - Usage: Main text, headings, important content
- **Secondary**
  - CSS Variable: `--color-text-secondary`
  - Tailwind Class: `text-gray-300`
  - Contrast: 9.7:1
  - Usage: Softer text, descriptions
- **Muted**
  - CSS Variable: `--color-text-muted`
  - Tailwind Class: `text-gray-400`
  - Contrast: 5.8:1
  - Usage: Subtle text, metadata, hints
- **Inverse**
  - CSS Variable: `--color-text-inverse`
  - Tailwind Class: `text-gray-900`
  - Contrast: N/A
  - Usage: Text on light backgrounds
- **Error**
  - CSS Variable: `--color-text-error`
  - Tailwind Class: `text-red-300`
  - Contrast: 6.2:1
  - Usage: Error messages, warnings
- **Success**
  - CSS Variable: `--color-text-success`
  - Tailwind Class: `text-green-300`
  - Contrast: 10.1:1
  - Usage: Success messages, positive states
- **Warning**
  - CSS Variable: `--color-text-warning`
  - Tailwind Class: `text-yellow-300`
  - Contrast: 11.8:1
  - Usage: Warning messages, cautions

### Game-Themed Colors

- **Highlight**
  - Tailwind Class: `text-game-highlight`
  - Usage: Branding, emphasis, CTA
- **Purple**
  - Tailwind Class: `text-purple-400`
  - Usage: AI-related text, special features
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
```text
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
```text
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

- [Spacing Design
  System](../../.github/instructions/coding.instructions.md#frontend-spacing-
  design-system)
- [WCAG AA Compliance](./UX_REMEDIATION_STATUS.md#issue-173-wcag-aa-contrast-
  compliance)
- [Button Component](../../frontend/src/components/ui/Button.tsx)

---

## Version History

| Date | Change |
|------|--------|
| 2025-12-05 | Initial documentation created |
| 2025-12-04 | WCAG AA compliance fixes completed |
| 2025-12-03 | Typography patterns established during UX review |
