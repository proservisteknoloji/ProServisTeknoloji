const fs = require('fs');
const file = 'C:/Users/umits/Desktop/ProservisProje_web_compile/proservis-agent-desktop/Services/SnmpCollector.cs';
let content = fs.readFileSync(file, 'utf8');

const oidBlock = `    private const string OidSysName = "1.3.6.1.2.1.1.5.0";
    private const string OidSysDescr = "1.3.6.1.2.1.1.1.0";
    private const string OidPrinterSerial = "1.3.6.1.2.1.43.5.1.1.17.1";
    private const string OidRicohSerial = "1.3.6.1.4.1.367.3.2.1.2.1.4.0";
    private const string OidCanonSerial = "1.3.6.1.4.1.1602.1.11.1.3.1.4.2.0";
    private const string OidXeroxSerial = "1.3.6.1.4.1.253.8.53.3.2.1.3.1";
    private const string OidInterfaceMacBase1 = "1.3.6.1.2.1.2.2.1.6.1";
    private const string OidInterfaceMacBase2 = "1.3.6.1.2.1.2.2.1.6.2";
    private const string OidMarkerLifeCountPrefix = "1.3.6.1.2.1.43.10.2.1.4.1.";`;

content = content.replace(/    private const string OidSysName = "1\.3\.6\.1\.2\.1\.1\.5\.0";\r?\n    private const string OidSysDescr = "1\.3\.6\.1\.2\.1\.1\.1\.0";\r?\n    private const string OidPrinterSerial = "1\.3\.6\.1\.2\.1\.43\.5\.1\.1\.17\.1";\r?\n    private const string OidMarkerLifeCountPrefix = "1\.3\.6\.1\.2\.1\.43\.10\.2\.1\.4\.1\.";/g, oidBlock);

const serialBlock = `            var serial = await GetStringAsync(endpoint, community, OidPrinterSerial, timeout, retries, cancellationToken);
            if (string.IsNullOrWhiteSpace(serial) && string.Equals(detectedBrand, "Ricoh", StringComparison.OrdinalIgnoreCase))
                serial = await GetStringAsync(endpoint, community, OidRicohSerial, timeout, retries, cancellationToken);
            if (string.IsNullOrWhiteSpace(serial) && string.Equals(detectedBrand, "Canon", StringComparison.OrdinalIgnoreCase))
                serial = await GetStringAsync(endpoint, community, OidCanonSerial, timeout, retries, cancellationToken);
            if (string.IsNullOrWhiteSpace(serial) && string.Equals(detectedBrand, "Xerox", StringComparison.OrdinalIgnoreCase))
                serial = await GetStringAsync(endpoint, community, OidXeroxSerial, timeout, retries, cancellationToken);

            if (string.IsNullOrWhiteSpace(serial))
            {
                var macRaw = await GetStringAsync(endpoint, community, OidInterfaceMacBase1, timeout, retries, cancellationToken);
                if (string.IsNullOrWhiteSpace(macRaw))
                    macRaw = await GetStringAsync(endpoint, community, OidInterfaceMacBase2, timeout, retries, cancellationToken);
                
                if (!string.IsNullOrWhiteSpace(macRaw))
                {
                    var macClean = new string(macRaw.Where(c => char.IsLetterOrDigit(c)).ToArray());
                    serial = "MAC-" + macClean.ToUpperInvariant();
                }
            }

            if (string.IsNullOrWhiteSpace(serial)) return null;`;

content = content.replace(/            var serial = await GetStringAsync\(endpoint, community, OidPrinterSerial, timeout, retries, cancellationToken\);\r?\n            if \(string\.IsNullOrWhiteSpace\(serial\)\) return null;/g, serialBlock);

fs.writeFileSync(file, content, 'utf8');
console.log('Patch complete.');
