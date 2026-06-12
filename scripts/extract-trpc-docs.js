const fs = require('fs');
const path = require('path');

const routerPath = path.join(__dirname, '../frontend/src/lib/trpc/router.ts');
const outputPath = path.join(__dirname, '../.planning/codebase/TRPC_API.md');

function extractDocs() {
    if (!fs.existsSync(routerPath)) {
        console.error('Router file not found at:', routerPath);
        return;
    }

    const content = fs.readFileSync(routerPath, 'utf8');
    const lines = content.split('\n');
    const docs = [];

    docs.push('# 📡 tRPC API Documentation');
    docs.push(`*Last Updated: ${new Date().toLocaleString()}*`);
    docs.push('');
    docs.push('Automated documentation for Nexus tRPC endpoints.');
    docs.push('');

    let currentMethod = null;
    let currentDesc = null;
    let currentInput = null;

    // A simple parser for the specific pattern in router.ts
    const methodRegex = /^\s*([a-zA-Z0-9]+):\s*publicProcedure/;
    const descRegex = /\.meta\(\{\s*description:\s*['"](.+?)['"]\s*\}\)/;
    const inputRegex = /\.input\(z\.object\(\{(.+?)\}\)\)/s;

    let i = 0;
    while (i < lines.length) {
        const line = lines[i];
        
        const methodMatch = line.match(methodRegex);
        if (methodMatch) {
            currentMethod = methodMatch[1];
            
            // Look ahead for meta and input
            let lookAhead = "";
            for(let j = 1; j < 20; j++) {
                if (lines[i+j]) lookAhead += lines[i+j];
            }

            const descMatch = lookAhead.match(descRegex);
            const inputMatch = lookAhead.match(inputRegex);

            docs.push(`### \`${currentMethod}\``);
            if (descMatch) docs.push(`**Description**: ${descMatch[1]}`);
            
            if (inputMatch) {
                const fields = inputMatch[1].trim().split(',').map(f => f.trim()).filter(f => f);
                docs.push('**Input**:');
                fields.forEach(f => docs.push(`- \`${f}\``));
            } else {
                docs.push('**Input**: None');
            }
            
            const type = lookAhead.includes('.query(') ? 'QUERY' : 'MUTATION';
            docs.push(`**Type**: \`${type}\``);
            docs.push('');
        }
        i++;
    }

    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, docs.join('\n'));
    console.log('Successfully generated tRPC documentation at:', outputPath);
}

extractDocs();
