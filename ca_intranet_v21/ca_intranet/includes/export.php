<?php
/**
 * CLEAN CSV EXPORT HELPER
 * Works in Excel, LibreOffice, OpenOffice, Google Sheets
 * Uses UTF-8 BOM so Excel opens it correctly without encoding issues
 */

function startCSVDownload($filename) {
    // Clean any output buffer
    while (ob_get_level()) ob_end_clean();
    header('Content-Type: text/csv; charset=UTF-8');
    header('Content-Disposition: attachment; filename="' . $filename . '.csv"');
    header('Cache-Control: no-cache, no-store, must-revalidate');
    header('Pragma: no-cache');
    header('Expires: 0');
    // UTF-8 BOM — makes Excel auto-detect encoding correctly
    echo "\xEF\xBB\xBF";
}

function writeCSVRow($handle, $fields) {
    // Ensure all values are strings, handle nulls
    $clean = array_map(function($v) {
        if ($v === null) return '';
        $v = (string)$v;
        // Remove line breaks within cells
        $v = str_replace(["\r\n", "\r", "\n"], ' ', $v);
        return $v;
    }, $fields);
    fputcsv($handle, $clean);
}

function outputCSV($headers, $rows_callback) {
    $out = fopen('php://output', 'w');
    // Write header
    writeCSVRow($out, $headers);
    // Write data rows via callback
    $rows_callback($out);
    fclose($out);
    exit;
}
