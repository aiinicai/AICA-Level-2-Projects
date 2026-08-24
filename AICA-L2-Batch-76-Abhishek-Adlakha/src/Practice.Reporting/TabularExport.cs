using System.Globalization;
using System.IO.Compression;
using System.Text;
using System.Xml;

namespace Practice.Reporting;

public sealed record ExportColumn(string Header, bool Numeric = false);

public static class TabularExport
{
    public static byte[] Csv(IReadOnlyList<ExportColumn> columns, IEnumerable<IReadOnlyList<string>> rows)
    {
        var output = new StringBuilder("\uFEFF");
        output.AppendLine(string.Join(',', columns.Select(column => EscapeCsv(column.Header))));
        foreach (var row in rows) output.AppendLine(string.Join(',', row.Select(EscapeCsv)));
        return Encoding.UTF8.GetBytes(output.ToString());
    }

    public static byte[] Xlsx(string sheetName, IReadOnlyList<ExportColumn> columns, IEnumerable<IReadOnlyList<string>> rows)
    {
        using var stream = new MemoryStream();
        using (var archive = new ZipArchive(stream, ZipArchiveMode.Create, true))
        {
            WriteText(archive, "[Content_Types].xml", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/><Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/></Types>");
            WriteText(archive, "_rels/.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/></Relationships>");
            WriteText(archive, "xl/workbook.xml", $"<?xml version=\"1.0\" encoding=\"UTF-8\"?><workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets><sheet name=\"{XmlEscape(SafeSheetName(sheetName))}\" sheetId=\"1\" r:id=\"rId1\"/></sheets></workbook>");
            WriteText(archive, "xl/_rels/workbook.xml.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/></Relationships>");
            var entry = archive.CreateEntry("xl/worksheets/sheet1.xml", CompressionLevel.Fastest);
            using var writer = XmlWriter.Create(entry.Open(), new XmlWriterSettings { Encoding = new UTF8Encoding(false), CloseOutput = true });
            writer.WriteStartDocument(); writer.WriteStartElement("worksheet", "http://schemas.openxmlformats.org/spreadsheetml/2006/main"); writer.WriteStartElement("sheetData");
            WriteRow(writer, columns.Select(column => column.Header).ToArray(), new HashSet<int>());
            var numericColumns = columns.Select((column, index) => (column, index)).Where(item => item.column.Numeric).Select(item => item.index).ToHashSet();
            foreach (var row in rows) WriteRow(writer, row, numericColumns);
            writer.WriteEndElement(); writer.WriteEndElement(); writer.WriteEndDocument();
        }
        return stream.ToArray();
    }

    private static string EscapeCsv(string value)
    {
        if (value.Length > 0 && "=+-@".Contains(value[0])) value = "'" + value;
        return $"\"{value.Replace("\"", "\"\"")}\"";
    }

    private static void WriteText(ZipArchive archive, string path, string content)
    {
        var entry = archive.CreateEntry(path, CompressionLevel.Fastest);
        using var writer = new StreamWriter(entry.Open(), new UTF8Encoding(false)); writer.Write(content);
    }

    private static void WriteRow(XmlWriter writer, IReadOnlyList<string> values, HashSet<int> numericColumns)
    {
        writer.WriteStartElement("row");
        for (var index = 0; index < values.Count; index++)
        {
            var value = values[index]; writer.WriteStartElement("c");
            if (numericColumns.Contains(index) && decimal.TryParse(value, NumberStyles.Number, CultureInfo.InvariantCulture, out _)) writer.WriteElementString("v", value);
            else { writer.WriteAttributeString("t", "inlineStr"); writer.WriteStartElement("is"); writer.WriteElementString("t", value); writer.WriteEndElement(); }
            writer.WriteEndElement();
        }
        writer.WriteEndElement();
    }

    private static string SafeSheetName(string value)
    {
        var safe = new string(value.Where(character => !"[]:*?/\\".Contains(character)).ToArray());
        return string.IsNullOrWhiteSpace(safe) ? "Report" : safe[..Math.Min(31, safe.Length)];
    }

    private static string XmlEscape(string value) => System.Security.SecurityElement.Escape(value) ?? string.Empty;
}
