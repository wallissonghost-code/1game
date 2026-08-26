const fs = require('fs');

const file = 'game.html';
if (!fs.existsSync(file)) {
  console.error('QA FAIL: game.html nao encontrado');
  process.exit(1);
}

const src = fs.readFileSync(file, 'utf8');
const failures = [];
const warnings = [];

function requireAny(label, patterns) {
  if (!patterns.some((p) => p.test(src))) failures.push(label);
}

// Contratos basicos da batalha. Estes testes sao intencionalmente estruturais:
// impedem regressao silenciosa de recursos essenciais sem acoplar o QA a nomes exatos.
requireAny('loop de animacao ausente', [/requestAnimationFrame\s*\(/]);
requireAny('canvas/campo de batalha ausente', [/<canvas\b/i, /battlefield/i, /campo.?de.?batalha/i]);
requireAny('logica de unidades/mobs ausente', [/\bmobs?\b/i, /\bunits?\b/i, /tropas?/i]);
requireAny('suporte ao paladino ausente', [/paladin/i, /paladino/i]);
requireAny('logica de times ausente', [/chaos/i, /caos/i, /redTeam/i, /blueTeam/i, /reino.?da.?luz/i]);
requireAny('vida de castelo ausente', [/castle.*(?:hp|health|life|vida)/i, /(?:hp|health|life|vida).*castle/i, /castelo/i]);

// Sinais que costumam causar os bugs visuais vistos durante testes manuais.
if (!/(spacing|separation|formation|lane|slot|offset|gap)/i.test(src)) {
  warnings.push('Nao encontrei contrato explicito de espacamento/formacao entre unidades.');
}
if (!/(direction|facing|orientation|heading|angle)/i.test(src)) {
  warnings.push('Nao encontrei contrato explicito de direcao/orientacao dos sprites.');
}
if (!/(fps|performance|frameBudget|deltaTime|\bdt\b)/i.test(src)) {
  warnings.push('Nao encontrei instrumentacao/controle explicito de performance.');
}

console.log('=== 1GAME GAMEPLAY QA ===');
console.log(`game.html: ${src.length} bytes`);
warnings.forEach((w) => console.warn('QA WARN:', w));

if (failures.length) {
  failures.forEach((f) => console.error('QA FAIL:', f));
  process.exit(1);
}

console.log('QA PASS: contratos estruturais essenciais encontrados.');
