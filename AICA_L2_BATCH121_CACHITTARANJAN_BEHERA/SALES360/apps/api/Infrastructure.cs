using Npgsql;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Security.Cryptography;
using System.Text;

namespace Sales360.Api;
public class Store(string connectionString)
{
    public async Task<NpgsqlConnection> Open() { var c = new NpgsqlConnection(connectionString); await c.OpenAsync(); return c; }
    public static NpgsqlCommand Command(NpgsqlConnection c, string sql, params object?[] args)
    {
        var cmd = new NpgsqlCommand(sql,c);
        for(var i=0;i<args.Length;i++) cmd.Parameters.AddWithValue("p"+i,args[i]??DBNull.Value);
        return cmd;
    }
    public static async Task<int> Exec(NpgsqlConnection c,string sql,params object?[] args) { await using var cmd=Command(c,sql,args); return await cmd.ExecuteNonQueryAsync(); }
    public static async Task<JsonArray> Rows(NpgsqlConnection c,string sql,params object?[] args)
    {
        await using var cmd=Command(c,sql,args); await using var reader=await cmd.ExecuteReaderAsync(); var rows=new JsonArray();
        while(await reader.ReadAsync()) { var row=new JsonObject(); for(var i=0;i<reader.FieldCount;i++) { var name=reader.GetName(i); if(reader.IsDBNull(i)) row[name]=null; else if(reader.GetDataTypeName(i)=="jsonb") row[name]=JsonNode.Parse(reader.GetString(i)); else row[name]=JsonSerializer.SerializeToNode(reader.GetValue(i)); } rows.Add(row); } return rows;
    }
    public static async Task<JsonObject> One(NpgsqlConnection c,string sql,params object?[] args) => (await Rows(c,sql,args)).FirstOrDefault()?.AsObject() ?? throw new KeyNotFoundException("Record not found in this company.");
    public async Task<T> Transaction<T>(string company, Func<NpgsqlConnection,Task<T>> action)
    {
        await using var c=await Open(); await using var tx=await c.BeginTransactionAsync();
        await Exec(c,"SELECT pg_advisory_xact_lock(hashtext(@p0))",company);
        var result=await action(c); await tx.CommitAsync(); return result;
    }
    public static async Task Audit(NpgsqlConnection c,string company,string actor,string action,string entity,object payload)
    {
        var prior=(await Rows(c,"SELECT hash FROM audit_event WHERE company_id=@p0 ORDER BY sequence DESC LIMIT 1",company)).FirstOrDefault()?["hash"]?.ToString()??"GENESIS";
        var json=JsonSerializer.Serialize(payload); var hash=Hash(prior+company+actor+action+entity+json);
        await Exec(c,"INSERT INTO audit_event(company_id,actor,action,entity_id,payload,previous_hash,hash,canonical_payload) VALUES(@p0,@p1,@p2,@p3,@p4::jsonb,@p5,@p6,@p4)",company,actor,action,entity,json,prior,hash);
    }
    public static string Hash(string text)=>Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(text))).ToLowerInvariant();
    public static string Password(string password) { var salt=RandomNumberGenerator.GetBytes(16); var hash=Rfc2898DeriveBytes.Pbkdf2(password,salt,210000,HashAlgorithmName.SHA256,32); return Convert.ToBase64String(salt)+":"+Convert.ToBase64String(hash); }
    public static bool Verify(string password,string stored) { var parts=stored.Split(':'); var hash=Rfc2898DeriveBytes.Pbkdf2(password,Convert.FromBase64String(parts[0]),210000,HashAlgorithmName.SHA256,32); return CryptographicOperations.FixedTimeEquals(hash,Convert.FromBase64String(parts[1])); }
}
public static class JsonFields
{
    public static string Text(this JsonNode? n,string key)=>n?[key]?.ToString().Trim()??"";
    public static decimal Decimal(this JsonNode? n,string key)=>decimal.TryParse(n?[key]?.ToString(),System.Globalization.NumberStyles.Number,System.Globalization.CultureInfo.InvariantCulture,out var value)?value:throw new Sales360.Domain.RuleException($"{key} must be a valid number.");
    public static int Integer(this JsonNode n,string key)=>int.Parse(n.Text(key));
    public static DateOnly Date(this JsonNode n,string key)=>DateOnly.TryParseExact(n.Text(key),"yyyy-MM-dd",out var date)?date:throw new Sales360.Domain.RuleException($"{key} must be YYYY-MM-DD.");
}
