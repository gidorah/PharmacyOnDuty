# Specification: Fix Sitemap NoReverseMatch Error

## Overview
The application is experiencing a `NoReverseMatch` error in the sitemap generation because `sitemaps.py` references a URL named `pharmacies_list`, which does not exist in the URL configuration. The correct URL name for the main landing page is `home`. This track aims to resolve this crash and prevent future regressions.

## Functional Requirements
1.  **Fix Sitemap Configuration:** Update `PharmacyOnDuty/sitemaps.py` to use the URL name `home` instead of `pharmacies_list`.
2.  **Verify References:** Ensure no other parts of the codebase (templates, views, tests) incorrectly reference `pharmacies_list` as a URL name.
3.  **Sitemap Generation:** The sitemap must be generated successfully without raising a `NoReverseMatch` exception.

## Non-Functional Requirements
1.  **Code Consistency:** Maintain the `home` naming convention for the landing page URL as established in `urls.py`.

## Acceptance Criteria
1.  Running the sitemap generation command (or accessing `/sitemap.xml`) succeeds without error.
2.  The `home` page URL is correctly included in the generated sitemap.
3.  A new or updated test case verifies that the sitemap can be generated successfully.
4.  Grep/Search confirms `pharmacies_list` is not used as a URL name argument in `reverse()` calls or `{% url %}` tags.

## Out of Scope
*   Refactoring the view function name `pharmacies_list` itself (only the URL name usage is in scope).
*   Fixing other Sentry issues unrelated to the sitemap crash.
