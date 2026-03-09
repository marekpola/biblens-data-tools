# Import of recognition language packs

## Purpose

`biblens-data-tools` contains utilities that convert upstream language data
into the JSON format used by the BibLens data repository (`biblens-data`).

The goal is to extract book-name aliases from external projects and transform
them into BibLens **recognition language packs**.

The resulting files are stored in the `biblens-data` repository under:

recognition-languages/{id}.json


## Target format

Each generated file must follow the `LanguagePackFile` structure used by
BibLens:

```ts
type LanguagePackFile = {
  id: string;
  displayName: string;
  lang: string;
  formatVersion: number;
  source?: string;
  books: Record<string, { aliases: string[] }>; // USFM BookId → alias list
};
```


## Source data

Initial import source:

openbibleinfo / Bible-Passage-Reference-Parser-Languages  
https://github.com/openbibleinfo/Bible-Passage-Reference-Parser-Languages

Example file:

lang/ces.js


## Output

Example output file:

recognition-languages/cs.json

Example structure:

```json
{
  "id": "cs",
  "displayName": "Czech",
  "lang": "cs",
  "formatVersion": 1,
  "source": "openbibleinfo/Bible-Passage-Reference-Parser-Languages/lang/ces.js",
  "books": {
    "GEN": {
      "aliases": ["Genesis", "Gn", "1. Mojžíšova"]
    }
  }
}
```


## Processing rules

The import tool must:

- extract book-name aliases from the upstream source
- map upstream book identifiers to **USFM BookId**
- remove duplicate aliases
- remove empty aliases
- preserve diacritics
- produce deterministic JSON output


## Scope of this task

This tool currently generates only:

recognition-languages/{lang}.json


The following are **not part of this task**:

- generation of `reference-formats`
- repository catalog generation
- downloading sources from GitHub
- runtime integration with the upstream parser


## License notice

Source data may be derived from:

Bible-Passage-Reference-Parser  
https://github.com/openbibleinfo/Bible-Passage-Reference-Parser

License: MIT