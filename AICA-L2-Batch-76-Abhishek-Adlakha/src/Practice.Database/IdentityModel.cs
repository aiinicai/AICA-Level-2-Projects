using Microsoft.EntityFrameworkCore;
using Practice.Database.Entities;

namespace Practice.Database;

internal static class IdentityModel
{
    public static void Configure(ModelBuilder modelBuilder)
    {
        ConfigureUsers(modelBuilder);
        ConfigureRbac(modelBuilder);
        ConfigureEmployees(modelBuilder);
        ConfigureFieldPolicies(modelBuilder);
    }

    private static void ConfigureUsers(ModelBuilder modelBuilder)
    {
        var user = modelBuilder.Entity<LoginUser>();
        user.ToTable("users", "identity", table =>
        {
            table.HasCheckConstraint("ck_users_mobile_username", "mobile_username ~ '^[0-9]{10}$'");
            table.HasCheckConstraint("ck_users_failed_login_count", "failed_login_count >= 0");
        });
        user.HasKey(x => x.Id).HasName("pk_users");
        user.Property(x => x.Id).HasColumnName("id");
        user.Property(x => x.MobileUsername).HasColumnName("mobile_username").HasMaxLength(10).IsFixedLength();
        user.Property(x => x.PasswordHash).HasColumnName("password_hash");
        user.Property(x => x.SecurityStamp).HasColumnName("security_stamp").HasMaxLength(100);
        user.Property(x => x.MustChangePassword).HasColumnName("must_change_password");
        user.Property(x => x.IsActive).HasColumnName("is_active");
        user.Property(x => x.FailedLoginCount).HasColumnName("failed_login_count");
        user.Property(x => x.LockedUntilUtc).HasColumnName("locked_until_utc");
        user.Property(x => x.LastLoginAtUtc).HasColumnName("last_login_at_utc");
        user.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        user.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        user.HasIndex(x => x.MobileUsername).IsUnique().HasDatabaseName("ux_users_mobile_username");
        user.HasIndex(x => x.IsActive).HasDatabaseName("ix_users_active");

        var session = modelBuilder.Entity<UserSession>();
        session.ToTable("user_sessions", "identity", table => table.HasCheckConstraint(
            "ck_user_sessions_token_hash", "octet_length(token_hash) = 32"));
        session.HasKey(x => x.Id).HasName("pk_user_sessions");
        session.Property(x => x.Id).HasColumnName("id");
        session.Property(x => x.UserId).HasColumnName("user_id");
        session.Property(x => x.TokenHash).HasColumnName("token_hash");
        session.Property(x => x.SecurityStamp).HasColumnName("security_stamp").HasMaxLength(100);
        session.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        session.Property(x => x.LastSeenAtUtc).HasColumnName("last_seen_at_utc");
        session.Property(x => x.ExpiresAtUtc).HasColumnName("expires_at_utc");
        session.Property(x => x.RevokedAtUtc).HasColumnName("revoked_at_utc");
        session.Property(x => x.RevocationReason).HasColumnName("revocation_reason").HasMaxLength(300);
        session.Property(x => x.IpHash).HasColumnName("ip_hash");
        session.Property(x => x.UserAgent).HasColumnName("user_agent").HasMaxLength(500);
        session.HasOne(x => x.User).WithMany(x => x.Sessions).HasForeignKey(x => x.UserId)
            .OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_user_sessions_user");
        session.HasIndex(x => x.TokenHash).IsUnique().HasDatabaseName("ux_user_sessions_token_hash");
        session.HasIndex(x => new { x.UserId, x.RevokedAtUtc }).HasDatabaseName("ix_user_sessions_user_active");
        session.HasIndex(x => x.ExpiresAtUtc).HasDatabaseName("ix_user_sessions_expires");
    }

    private static void ConfigureRbac(ModelBuilder modelBuilder)
    {
        var role = modelBuilder.Entity<Role>();
        role.ToTable("roles", "identity");
        role.HasKey(x => x.Id).HasName("pk_roles");
        role.Property(x => x.Id).HasColumnName("id");
        role.Property(x => x.Code).HasColumnName("code").HasMaxLength(50);
        role.Property(x => x.Name).HasColumnName("name").HasMaxLength(100);
        role.Property(x => x.Description).HasColumnName("description").HasMaxLength(500);
        role.Property(x => x.IsSystem).HasColumnName("is_system");
        role.Property(x => x.IsProtected).HasColumnName("is_protected");
        role.Property(x => x.IsActive).HasColumnName("is_active");
        role.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        role.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        role.HasIndex(x => x.Code).IsUnique().HasDatabaseName("ux_roles_code");
        role.HasIndex(x => x.Name).IsUnique().HasDatabaseName("ux_roles_name");
        role.HasData(IdentitySeed.Roles);

        var permission = modelBuilder.Entity<PermissionDefinition>();
        permission.ToTable("permissions", "identity");
        permission.HasKey(x => x.Id).HasName("pk_permissions");
        permission.Property(x => x.Id).HasColumnName("id");
        permission.Property(x => x.Code).HasColumnName("code").HasMaxLength(120);
        permission.Property(x => x.Module).HasColumnName("module").HasMaxLength(50);
        permission.Property(x => x.Action).HasColumnName("action").HasMaxLength(50);
        permission.Property(x => x.Description).HasColumnName("description").HasMaxLength(500);
        permission.Property(x => x.SupportsScope).HasColumnName("supports_scope");
        permission.HasIndex(x => x.Code).IsUnique().HasDatabaseName("ux_permissions_code");
        permission.HasIndex(x => new { x.Module, x.Action }).HasDatabaseName("ix_permissions_module_action");
        permission.HasData(IdentitySeed.Permissions);

        var userRole = modelBuilder.Entity<UserRole>();
        userRole.ToTable("user_roles", "identity");
        userRole.HasKey(x => new { x.UserId, x.RoleId }).HasName("pk_user_roles");
        userRole.Property(x => x.UserId).HasColumnName("user_id");
        userRole.Property(x => x.RoleId).HasColumnName("role_id");
        userRole.Property(x => x.AssignedAtUtc).HasColumnName("assigned_at_utc");
        userRole.Property(x => x.AssignedByUserId).HasColumnName("assigned_by_user_id");
        userRole.HasOne(x => x.User).WithMany(x => x.UserRoles).HasForeignKey(x => x.UserId)
            .OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_user_roles_user");
        userRole.HasOne(x => x.Role).WithMany(x => x.UserRoles).HasForeignKey(x => x.RoleId)
            .OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_user_roles_role");
        userRole.HasIndex(x => new { x.RoleId, x.UserId }).HasDatabaseName("ix_user_roles_role_user");

        var rolePermission = modelBuilder.Entity<RolePermissionGrant>();
        rolePermission.ToTable("role_permissions", "identity", table => table.HasCheckConstraint(
            "ck_role_permissions_scope", "scope_ceiling IN ('OWN', 'TEAM', 'ALL')"));
        rolePermission.HasKey(x => new { x.RoleId, x.PermissionId }).HasName("pk_role_permissions");
        rolePermission.Property(x => x.RoleId).HasColumnName("role_id");
        rolePermission.Property(x => x.PermissionId).HasColumnName("permission_id");
        rolePermission.Property(x => x.ScopeCeiling).HasColumnName("scope_ceiling").HasMaxLength(10);
        rolePermission.HasOne(x => x.Role).WithMany(x => x.RolePermissions).HasForeignKey(x => x.RoleId)
            .OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_role_permissions_role");
        rolePermission.HasOne(x => x.Permission).WithMany(x => x.RolePermissions).HasForeignKey(x => x.PermissionId)
            .OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_role_permissions_permission");
        rolePermission.HasIndex(x => new { x.PermissionId, x.RoleId }).HasDatabaseName("ix_role_permissions_permission_role");
        rolePermission.HasData(IdentitySeed.AdministratorPermissions);
    }

    private static void ConfigureEmployees(ModelBuilder modelBuilder)
    {
        var employee = modelBuilder.Entity<Employee>();
        employee.ToTable("employees", "employees", table =>
        {
            table.HasCheckConstraint("ck_employees_mobile", "mobile_number IS NULL OR mobile_number ~ '^[0-9]{10}$'");
            table.HasCheckConstraint("ck_employees_dates", "left_on IS NULL OR joined_on IS NULL OR left_on >= joined_on");
        });
        employee.HasKey(x => x.Id).HasName("pk_employees");
        employee.Property(x => x.Id).HasColumnName("id");
        employee.Property(x => x.UserId).HasColumnName("user_id");
        employee.Property(x => x.EmployeeCode).HasColumnName("employee_code").HasMaxLength(30);
        employee.Property(x => x.NormalizedEmployeeCode).HasColumnName("normalized_employee_code").HasMaxLength(30);
        employee.Property(x => x.DisplayName).HasColumnName("display_name").HasMaxLength(200);
        employee.Property(x => x.Email).HasColumnName("email").HasMaxLength(320);
        employee.Property(x => x.MobileNumber).HasColumnName("mobile_number").HasMaxLength(10).IsFixedLength();
        employee.Property(x => x.Designation).HasColumnName("designation").HasMaxLength(100);
        employee.Property(x => x.Department).HasColumnName("department").HasMaxLength(100);
        employee.Property(x => x.ManagerEmployeeId).HasColumnName("manager_employee_id");
        employee.Property(x => x.JoinedOn).HasColumnName("joined_on");
        employee.Property(x => x.LeftOn).HasColumnName("left_on");
        employee.Property(x => x.IsActive).HasColumnName("is_active");
        employee.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        employee.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        employee.HasOne(x => x.User).WithOne().HasForeignKey<Employee>(x => x.UserId)
            .OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_employees_user");
        employee.HasOne(x => x.ManagerEmployee).WithMany(x => x.DirectReports).HasForeignKey(x => x.ManagerEmployeeId)
            .OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_employees_manager");
        employee.HasIndex(x => x.UserId).IsUnique().HasFilter("user_id IS NOT NULL").HasDatabaseName("ux_employees_user");
        employee.HasIndex(x => x.NormalizedEmployeeCode).IsUnique().HasDatabaseName("ux_employees_code");
        employee.HasIndex(x => new { x.ManagerEmployeeId, x.IsActive }).HasDatabaseName("ix_employees_manager_active");
        employee.HasIndex(x => new { x.DisplayName, x.IsActive }).HasDatabaseName("ix_employees_name_active");

        var team = modelBuilder.Entity<Team>();
        team.ToTable("teams", "employees");
        team.HasKey(x => x.Id).HasName("pk_teams");
        team.Property(x => x.Id).HasColumnName("id");
        team.Property(x => x.Code).HasColumnName("code").HasMaxLength(30);
        team.Property(x => x.Name).HasColumnName("name").HasMaxLength(100);
        team.Property(x => x.ManagerEmployeeId).HasColumnName("manager_employee_id");
        team.Property(x => x.IsActive).HasColumnName("is_active");
        team.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        team.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        team.HasOne(x => x.ManagerEmployee).WithMany().HasForeignKey(x => x.ManagerEmployeeId)
            .OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_teams_manager");
        team.HasIndex(x => x.Code).IsUnique().HasDatabaseName("ux_teams_code");
        team.HasIndex(x => x.Name).IsUnique().HasDatabaseName("ux_teams_name");

        var membership = modelBuilder.Entity<TeamMembership>();
        membership.ToTable("team_memberships", "employees", table => table.HasCheckConstraint(
            "ck_team_memberships_dates", "valid_to IS NULL OR valid_to >= valid_from"));
        membership.HasKey(x => new { x.TeamId, x.EmployeeId, x.ValidFrom }).HasName("pk_team_memberships");
        membership.Property(x => x.TeamId).HasColumnName("team_id");
        membership.Property(x => x.EmployeeId).HasColumnName("employee_id");
        membership.Property(x => x.ValidFrom).HasColumnName("valid_from");
        membership.Property(x => x.ValidTo).HasColumnName("valid_to");
        membership.Property(x => x.IsLead).HasColumnName("is_lead");
        membership.HasOne(x => x.Team).WithMany(x => x.Memberships).HasForeignKey(x => x.TeamId)
            .OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_team_memberships_team");
        membership.HasOne(x => x.Employee).WithMany(x => x.TeamMemberships).HasForeignKey(x => x.EmployeeId)
            .OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_team_memberships_employee");
        membership.HasIndex(x => new { x.EmployeeId, x.ValidTo }).HasDatabaseName("ix_team_memberships_employee_active");
    }

    private static void ConfigureFieldPolicies(ModelBuilder modelBuilder)
    {
        var field = modelBuilder.Entity<FieldDefinition>();
        field.ToTable("field_definitions", "system", table => table.HasCheckConstraint(
            "ck_field_definitions_required", "NOT is_system_required OR is_administrator_required"));
        field.HasKey(x => new { x.EntityType, x.FieldKey }).HasName("pk_field_definitions");
        field.Property(x => x.EntityType).HasColumnName("entity_type").HasMaxLength(100);
        field.Property(x => x.FieldKey).HasColumnName("field_key").HasMaxLength(100);
        field.Property(x => x.Label).HasColumnName("label").HasMaxLength(150);
        field.Property(x => x.Description).HasColumnName("description").HasMaxLength(500);
        field.Property(x => x.IsSystemRequired).HasColumnName("is_system_required");
        field.Property(x => x.IsAdministratorRequired).HasColumnName("is_administrator_required");
        field.Property(x => x.IsActive).HasColumnName("is_active");
        field.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        field.Property(x => x.UpdatedByUserId).HasColumnName("updated_by_user_id");
        field.HasIndex(x => new { x.EntityType, x.IsActive }).HasDatabaseName("ix_field_definitions_entity_active");
        field.HasData(IdentitySeed.EmployeeFields.Concat(IdentitySeed.ClientFields).Concat(IdentitySeed.ClientServiceFields).Concat(IdentitySeed.TaskFields).Concat(IdentitySeed.BillingFields));
    }
}
