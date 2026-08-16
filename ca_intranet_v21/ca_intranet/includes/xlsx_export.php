<?php
/**
 * MINIMAL XLSX GENERATOR WITH DROPDOWN DATA VALIDATION
 * No external libraries required — uses PHP's built-in ZipArchive.
 * Produces a real, valid .xlsx file that opens correctly in Excel,
 * LibreOffice Calc, and Google Sheets (via upload/import), with
 * native dropdown (data validation) cells to prevent typos on import.
 *
 * Falls back to plain CSV automatically if ZipArchive is not available
 * on the server (rare, but some minimal PHP builds omit it).
 */

function xlsxIsAvailable() {
    return class_exists('ZipArchive');
}

/**
 * Generate and stream an XLSX file with dropdown validation on specified columns.
 *
 * @param string $filename       Download filename (without extension)
 * @param array  $headers        Column header labels, e.g. ['Client Name','PAN',...]
 * @param array  $sample_rows    Array of arrays — sample/example data rows
 * @param array  $dropdowns      Map of column index (0-based) => array of allowed values
 *                                e.g. [9 => ['Monthly','QRMP','Composition']]
 * @param int    $dropdown_rows  How many data rows (below header) get the dropdown applied (default 500)
 */
function streamXLSXWithDropdowns($filename, $headers, $sample_rows, $dropdowns = [], $dropdown_rows = 500) {
    $tmpFile = tempnam(sys_get_temp_dir(), 'xlsx_');
    $zip = new ZipArchive();
    $zip->open($tmpFile, ZipArchive::CREATE | ZipArchive::OVERWRITE);

    // ── [Content_Types].xml ──────────────────────────────
    $zip->addFromString('[Content_Types].xml',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'.
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'.
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'.
        '<Default Extension="xml" ContentType="application/xml"/>'.
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'.
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'.
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'.
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'.
        '</Types>');

    // ── _rels/.rels ───────────────────────────────────────
    $zip->addFromString('_rels/.rels',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'.
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'.
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'.
        '</Relationships>');

    // ── xl/_rels/workbook.xml.rels ────────────────────────
    $zip->addFromString('xl/_rels/workbook.xml.rels',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'.
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'.
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'.
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'.
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'.
        '</Relationships>');

    // ── xl/workbook.xml ───────────────────────────────────
    $zip->addFromString('xl/workbook.xml',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'.
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '.
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'.
        '<sheets><sheet name="Import Data" sheetId="1" r:id="rId1"/></sheets>'.
        '</workbook>');

    // ── xl/styles.xml (header bold + background) ──────────
    $zip->addFromString('xl/styles.xml',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'.
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'.
        '<fonts count="2">'.
            '<font><sz val="11"/><name val="Calibri"/></font>'.
            '<font><sz val="11"/><name val="Calibri"/><b/><color rgb="FFFFFFFF"/></font>'.
        '</fonts>'.
        '<fills count="3">'.
            '<fill><patternFill patternType="none"/></fill>'.
            '<fill><patternFill patternType="gray125"/></fill>'.
            '<fill><patternFill patternType="solid"><fgColor rgb="FF1A4B8C"/><bgColor indexed="64"/></patternFill></fill>'.
        '</fills>'.
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'.
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'.
        '<cellXfs count="2">'.
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'.
            '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'.
        '</cellXfs>'.
        '</styleSheet>');

    // ── Build shared strings table ─────────────────────────
    // Collect every unique string used (headers + sample data) for sharedStrings.xml
    $shared = [];
    $sIndex = function($val) use (&$shared) {
        $val = (string)$val;
        if (!isset($shared[$val])) {
            $shared[$val] = count($shared);
        }
        return $shared[$val];
    };

    // Pre-register header and sample row strings
    foreach ($headers as $h) $sIndex($h);
    foreach ($sample_rows as $row) {
        foreach ($row as $cell) {
            if ($cell !== '' && $cell !== null) $sIndex($cell);
        }
    }

    // ── Build worksheet XML ────────────────────────────────
    $colLetter = function($n) {
        $letter = '';
        $n++;
        while ($n > 0) {
            $rem = ($n - 1) % 26;
            $letter = chr(65 + $rem) . $letter;
            $n = intval(($n - 1) / 26);
        }
        return $letter;
    };

    $rowsXML = '';
    // Header row (row 1) — bold style index 1
    $rowsXML .= '<row r="1">';
    foreach ($headers as $ci => $h) {
        $ref = $colLetter($ci) . '1';
        $rowsXML .= '<c r="'.$ref.'" t="s" s="1"><v>'.$sIndex($h).'</v></c>';
    }
    $rowsXML .= '</row>';

    // Sample data rows
    $r = 2;
    foreach ($sample_rows as $row) {
        $rowsXML .= '<row r="'.$r.'">';
        foreach ($row as $ci => $cell) {
            if ($cell === '' || $cell === null) continue;
            $ref = $colLetter($ci) . $r;
            $rowsXML .= '<c r="'.$ref.'" t="s"><v>'.$sIndex($cell).'</v></c>';
        }
        $rowsXML .= '</row>';
        $r++;
    }

    // ── Data validation (dropdown) definitions ─────────────
    $maxRow = max($dropdown_rows + 1, $r);
    $validationsXML = '';
    if (!empty($dropdowns)) {
        $validationsXML .= '<dataValidations count="'.count($dropdowns).'">';
        foreach ($dropdowns as $colIdx => $values) {
            $col = $colLetter($colIdx);
            // Excel inline list — comma separated, quoted; max ~255 chars per Excel limit
            $listStr = implode(',', array_map(function($v) {
                return str_replace(['"', ','], ['', ';'], $v); // sanitize for inline list safety
            }, $values));
            $range = $col.'2:'.$col.$maxRow;
            $validationsXML .= '<dataValidation type="list" allowBlank="1" showInputMessage="1" showErrorMessage="1" errorTitle="Invalid Entry" error="Please select a value from the dropdown list." sqref="'.$range.'">'.
                '<formula1>"'.$listStr.'"</formula1>'.
                '</dataValidation>';
        }
        $validationsXML .= '</dataValidations>';
    }

    $dimension = $colLetter(count($headers)-1) . $maxRow;

    $sheetXML =
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'.
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'.
        '<dimension ref="A1:'.$dimension.'"/>'.
        '<sheetViews><sheetView tabSelected="1" workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'.
        '<sheetFormatPr defaultRowHeight="15"/>'.
        '<cols>';
    foreach ($headers as $ci => $h) {
        $width = max(14, min(40, strlen($h) + 4));
        $sheetXML .= '<col min="'.($ci+1).'" max="'.($ci+1).'" width="'.$width.'" customWidth="1"/>';
    }
    $sheetXML .= '</cols>'.
        '<sheetData>'.$rowsXML.'</sheetData>'.
        $validationsXML.
        '</worksheet>';

    $zip->addFromString('xl/worksheets/sheet1.xml', $sheetXML);

    // ── xl/sharedStrings.xml ────────────────────────────────
    $sst = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'.
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="'.count($shared).'" uniqueCount="'.count($shared).'">';
    foreach ($shared as $str => $idx) {
        $escaped = htmlspecialchars($str, ENT_XML1 | ENT_QUOTES, 'UTF-8');
        $sst .= '<si><t xml:space="preserve">'.$escaped.'</t></si>';
    }
    $sst .= '</sst>';
    $zip->addFromString('xl/sharedStrings.xml', $sst);

    $zip->close();

    // ── Stream to browser ───────────────────────────────────
    while (ob_get_level()) ob_end_clean();
    header('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    header('Content-Disposition: attachment; filename="'.$filename.'.xlsx"');
    header('Content-Length: ' . filesize($tmpFile));
    header('Cache-Control: no-cache, no-store, must-revalidate');
    header('Pragma: no-cache');
    readfile($tmpFile);
    unlink($tmpFile);
    exit;
}
