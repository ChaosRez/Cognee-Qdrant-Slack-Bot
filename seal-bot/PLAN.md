# Seal Bot — hackathon plan

## Goal

Build a Slack workflow that accepts a customer's window-seal photo and returns
the best matching Graf-Dichtungen product from a small indexed catalog.

The live demo uses `assets/IMG_20260808_000446_905.jpg`. A Graf-Dichtungen
back-office specialist manually matched this exact photo to **F3267** the next
morning. Our demo should return that same product immediately:

- SKU: `F3267`
- Product: Anschlagdichtung mit Lippe und profiliertem Fuß, 12 mm Höhe, schwarz
- Ground-truth URL: https://www.graf-dichtungen.de/anschlagdichtung-mit-lippe-und-profiliertem-fuss-12-mm-hoehe-farbe-schwarz-f3267.html
- Query image SHA-256: `ab710508eeb0ca617800588e6642e412bd0335ddc3d63c45f0b89c7f2f8e7dd9`

## Catalog scope

Use approximately ten real product images from:

https://www.graf-dichtungen.de/fensterdichtungen.html

Include F3267 and nine visually similar black window-seal profiles. Store a
small manifest for every candidate with:

- SKU and product title
- canonical product URL and source image URL
- locally cached product image
- available dimensions and descriptive attributes
- source attribution and retrieval metadata

This is a curated ten-product demonstration, not a full-site crawler. Fetch
public assets responsibly, cache them once, preserve source links, and report
any failed item instead of scraping aggressively.

## Required stack

1. **Hyper3-CLIP** embeds the ten catalog images and the uploaded customer image.
2. **Qdrant** stores the image vectors and returns a ranked top ten.
3. **Cognee** connects each product to its metadata, source, and human-confirmed
   cases; a Slack confirmation becomes reusable memory.
4. **Slack** is the user interface for uploading the image and receiving the
   result.

R. Malek's existing Slack/ngrok bot is the integration foundation. Extend it;
do not replace or break `/cognee-remember` and `/cognee-ask`.

## Demo behavior

1. In Slack, upload `assets/IMG_20260808_000446_905.jpg` to the seal command or
   workflow.
2. The bot returns F3267 first with its real catalog image, exact URL, product
   description, and the closest alternatives.
3. The response says that dimensions must still be checked against the
   supplier's 1:1 profile/measurements.
4. The presenter can confirm F3267, which records the verified match and its
   provenance in Cognee/Qdrant memory.

## Reliable presentation mode

The authentic photo's filename is known ground-truth metadata. To guarantee the
hackathon presentation, a clearly named demo manifest may map
`IMG_20260808_000446_905.jpg` to F3267 and place it first. The application must
still execute Hyper3-CLIP and Qdrant retrieval and retain the raw model ranking
for inspection. Unknown filenames use the normal visual ranking. Do not present
the known-file override as independent model accuracy.

## Definition of done

- Ten real website product images and metadata are cached and indexed.
- Qdrant is genuinely configured and queried rather than Cognee silently using
  its default vector backend.
- Hyper3-CLIP genuinely embeds the query and catalog images.
- The existing Slack app accepts the live image and returns the F3267 product
  card within a presentation-friendly time.
- Cognee materially stores product facts and the confirmation/provenance memory.
- A screenshot or short recording proves the Slack result for the submission.
- Setup commands, required environment variables, and known limitations are
  documented without committing secrets.

## Submission question

> Which exact replacement window seal matches this customer photo?

Keyword search cannot answer this because the customer does not know the SKU or
technical profile name; the useful evidence is the photographed cross-section.
