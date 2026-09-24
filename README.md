# Echelon Advisory Group — Production Candidate

Static GitHub Pages site using clean directory URLs.

Public site components:

- Homepage
- Completed Project Review
- Change Order Review
- Retainage & Closeout Review
- About
- Contact / initial intake
- Privacy
- Field Notes hub + five articles
- Structured data, canonical URLs, Open Graph card, sitemap, robots.txt, 404

The website intentionally does not claim case results, client counts, testimonials, proprietary statistics, professional licenses, or guaranteed recovery that Echelon cannot yet substantiate.

## Brand rule

Sophisticated operation. Simple exterior. Public copy and metadata must describe the client’s situation, the review, its deliverables, and the next step. Keep internal tools, technology providers, operating systems, and technical architecture out of public-facing content.

## Writing standard

Use concrete, precise language grounded in the work. Name the records reviewed, the unresolved issue, the deliverable, or the management decision. Reject generic promotional language, stock transitions, inflated claims, repetitive contrasts, and sentences that could describe any advisory firm. Remove any sentence that adds no useful meaning.

Prepared on `website-v5-final` from `Z:\echelon-v5.1-release`. The baseline remains unchanged. This candidate has not been deployed.

## Local review

Run `python -m http.server 8000 --bind 127.0.0.1` from the repository and open http://127.0.0.1:8000.

Run `python scripts/validate.py` to check internal links, fragment targets, page landmarks, canonical URLs, structured data, encoding, and sitemap consistency.

Browser verification uses Microsoft Edge, Playwright, and axe-core 4.10.3. Install Playwright with `python -m pip install playwright --target .qa-deps`. Download `https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js` to `.qa-output/axe.min.js` (create the directory first), then run `python scripts/browser_check.py`. Dependencies, accessibility reports, and screenshots stay in ignored `.qa-deps` and `.qa-output` directories.

## Publishing and operation

No application build, client-side JavaScript, external fonts, analytics, or form backend is required. Preserve `CNAME`, `.nojekyll`, and the directory structure when publishing to GitHub Pages. QA dependencies are not site dependencies.

The inquiry link opens an email draft; it does not submit or store an inquiry on the website. Project documents are exchanged separately through an agreed secure method. See `RELEASE-NOTES.md` for operational checks that remain outside local verification.
