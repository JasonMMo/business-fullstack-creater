// Single-file Java launcher for L2 JDBC smoke (run via: java -cp <hsqldb.jar> _jdbc_smoke.java ...)
// Loads schema.sql + data.sql into an in-memory HSQLDB, optionally runs an
// invariant SELECT and asserts a scalar value. Statement separator: `^^` (matches
// live_overlay convention). Exit 0 = PASS, 1 = FAIL (with structured stderr).
//
// Args (positional):
//   --schema <path>          schema SQL (CREATE statements, `^^` separated)
//   --data   <path>          seed SQL (INSERT/MERGE statements, `^^` separated)
//   --invariant <sql>=<int>  optional: SELECT must return scalar equal to int
//
// All input files are UTF-8. Comments (-- ...) are stripped per line.
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

public class _jdbc_smoke {
    public static void main(String[] args) throws Exception {
        String schema = null, data = null, invariant = null;
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--schema":    schema    = args[++i]; break;
                case "--data":      data      = args[++i]; break;
                case "--invariant": invariant = args[++i]; break;
                default: System.err.println("[L2] unknown arg: " + args[i]); System.exit(2);
            }
        }
        if (schema == null || data == null) {
            System.err.println("[L2] usage: _jdbc_smoke --schema <file> --data <file> [--invariant <sql>=<int>]");
            System.exit(2);
        }
        Class.forName("org.hsqldb.jdbc.JDBCDriver");
        try (Connection c = DriverManager.getConnection("jdbc:hsqldb:mem:smoke", "SA", "")) {
            runFile(c, Path.of(schema), "schema");
            runFile(c, Path.of(data),   "data");
            if (invariant != null) {
                int eq = invariant.lastIndexOf('=');
                if (eq < 0) { System.err.println("[L2] --invariant requires <sql>=<int>"); System.exit(2); }
                String sql = invariant.substring(0, eq).trim();
                long expected = Long.parseLong(invariant.substring(eq + 1).trim());
                long got = -1;
                try (Statement st = c.createStatement(); ResultSet rs = st.executeQuery(sql)) {
                    if (rs.next()) got = rs.getLong(1);
                }
                if (got != expected) {
                    System.err.println("[L2] invariant FAIL: " + sql + " → " + got + " (expected " + expected + ")");
                    System.exit(1);
                }
                System.out.println("[L2] invariant OK: " + sql + " = " + got);
            }
            System.out.println("[L2] schema+data applied OK");
        } catch (Exception e) {
            System.err.println("[L2] FAIL: " + e.getClass().getSimpleName() + ": " + e.getMessage());
            System.exit(1);
        }
    }

    static void runFile(Connection c, Path p, String label) throws Exception {
        String raw = Files.readString(p);
        List<String> stmts = splitStatements(raw);
        try (Statement st = c.createStatement()) {
            int n = 0;
            for (String s : stmts) {
                if (s.isEmpty()) continue;
                try {
                    st.execute(s);
                    n++;
                } catch (Exception e) {
                    throw new RuntimeException(label + " stmt #" + (n + 1) + " failed: " + s.substring(0, Math.min(120, s.length())) + " — " + e.getMessage(), e);
                }
            }
            System.out.println("[L2] " + label + ": " + n + " stmts");
        }
    }

    // Split on `^^` (live_overlay convention) when present, else on `;`
    // (raw scaffold output). Strip `-- ` line comments either way.
    static List<String> splitStatements(String raw) {
        List<String> out = new ArrayList<>();
        String sep = raw.contains("^^") ? "\\^\\^" : ";";
        for (String chunk : raw.split(sep)) {
            StringBuilder sb = new StringBuilder();
            for (String line : chunk.split("\\r?\\n")) {
                String t = line;
                int idx = t.indexOf("--");
                if (idx >= 0) t = t.substring(0, idx);
                if (!t.isBlank()) sb.append(t).append('\n');
            }
            String s = sb.toString().trim();
            if (!s.isEmpty()) out.add(s);
        }
        return out;
    }
}
