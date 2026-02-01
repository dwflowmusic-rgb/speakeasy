# Palette's Journal - UX & Accessibility Learnings

## 2024-05-23 - Empty States in Data Lists
**Learning:** Users opening the History Window for the first time were greeted with a blank whitespace, which could be interpreted as a broken feature or loading error.
**Action:** Implemented a `QStackedWidget` pattern to toggle between the data list and a friendly "Empty State" widget. This pattern should be reused for any list-based views (e.g., if we add a "Favorites" list later).
