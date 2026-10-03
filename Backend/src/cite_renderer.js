const { Cite } = require('@citation-js/core');
require('@citation-js/plugin-csl');
require('@citation-js/plugin-bibtex');

let bibtexData = '';

process.stdin.on('data', chunk => {
    bibtexData += chunk;
});

process.stdin.on('end', async () => {
    try {
        const cite = await Cite.async(bibtexData);
        const output = cite.format('bibliography', {
            format: 'text',
            template: 'apa',
            lang: 'id-ID' // APA style, trying Indonesian locale if available, fallback en-US
        });
        console.log(output);
    } catch (e) {
        // Fallback: if citation-js fails to parse, return the raw data so at least something appears
        console.error("CSL processing error:", e);
        console.log(bibtexData);
    }
});
