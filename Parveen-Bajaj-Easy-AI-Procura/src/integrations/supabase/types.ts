export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.15"
  }
  public: {
    Tables: {
      approval_log: {
        Row: {
          action: string
          actor: string | null
          actor_name: string | null
          created_at: string
          doc_id: string
          doc_number: string | null
          doc_type: string
          id: string
          remarks: string | null
        }
        Insert: {
          action: string
          actor?: string | null
          actor_name?: string | null
          created_at?: string
          doc_id: string
          doc_number?: string | null
          doc_type: string
          id?: string
          remarks?: string | null
        }
        Update: {
          action?: string
          actor?: string | null
          actor_name?: string | null
          created_at?: string
          doc_id?: string
          doc_number?: string | null
          doc_type?: string
          id?: string
          remarks?: string | null
        }
        Relationships: []
      }
      departments: {
        Row: {
          created_at: string
          department_code: string
          department_name: string
          hod: string | null
          id: string
          status: Database["public"]["Enums"]["master_status"]
        }
        Insert: {
          created_at?: string
          department_code: string
          department_name: string
          hod?: string | null
          id?: string
          status?: Database["public"]["Enums"]["master_status"]
        }
        Update: {
          created_at?: string
          department_code?: string
          department_name?: string
          hod?: string | null
          id?: string
          status?: Database["public"]["Enums"]["master_status"]
        }
        Relationships: []
      }
      document_sequences: {
        Row: {
          doc_type: string
          last_seq: number
          year: number
        }
        Insert: {
          doc_type: string
          last_seq?: number
          year: number
        }
        Update: {
          doc_type?: string
          last_seq?: number
          year?: number
        }
        Relationships: []
      }
      grn_header: {
        Row: {
          approved_at: string | null
          approver: string | null
          approver_name: string | null
          checked_by: string | null
          created_at: string
          delivery_note_no: string | null
          department_id: string
          grn_date: string
          grn_number: string
          id: string
          lpo_id: string
          maker: string
          maker_name: string | null
          over_receipt_override: boolean
          receipt_status: Database["public"]["Enums"]["grn_receipt_status"]
          received_by: string | null
          reject_reason: string | null
          status: Database["public"]["Enums"]["doc_status"]
          supplier_id: string
        }
        Insert: {
          approved_at?: string | null
          approver?: string | null
          approver_name?: string | null
          checked_by?: string | null
          created_at?: string
          delivery_note_no?: string | null
          department_id: string
          grn_date?: string
          grn_number?: string
          id?: string
          lpo_id: string
          maker: string
          maker_name?: string | null
          over_receipt_override?: boolean
          receipt_status?: Database["public"]["Enums"]["grn_receipt_status"]
          received_by?: string | null
          reject_reason?: string | null
          status?: Database["public"]["Enums"]["doc_status"]
          supplier_id: string
        }
        Update: {
          approved_at?: string | null
          approver?: string | null
          approver_name?: string | null
          checked_by?: string | null
          created_at?: string
          delivery_note_no?: string | null
          department_id?: string
          grn_date?: string
          grn_number?: string
          id?: string
          lpo_id?: string
          maker?: string
          maker_name?: string | null
          over_receipt_override?: boolean
          receipt_status?: Database["public"]["Enums"]["grn_receipt_status"]
          received_by?: string | null
          reject_reason?: string | null
          status?: Database["public"]["Enums"]["doc_status"]
          supplier_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "grn_header_department_id_fkey"
            columns: ["department_id"]
            isOneToOne: false
            referencedRelation: "departments"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "grn_header_lpo_id_fkey"
            columns: ["lpo_id"]
            isOneToOne: false
            referencedRelation: "lpo_header"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "grn_header_supplier_id_fkey"
            columns: ["supplier_id"]
            isOneToOne: false
            referencedRelation: "suppliers"
            referencedColumns: ["id"]
          },
        ]
      }
      grn_lines: {
        Row: {
          grn_id: string
          id: string
          item_condition: Database["public"]["Enums"]["item_condition"]
          item_id: string
          lpo_line_id: string
          qty_ordered: number
          qty_received: number
          remarks: string | null
          shortage_excess: number | null
        }
        Insert: {
          grn_id: string
          id?: string
          item_condition?: Database["public"]["Enums"]["item_condition"]
          item_id: string
          lpo_line_id: string
          qty_ordered: number
          qty_received?: number
          remarks?: string | null
          shortage_excess?: number | null
        }
        Update: {
          grn_id?: string
          id?: string
          item_condition?: Database["public"]["Enums"]["item_condition"]
          item_id?: string
          lpo_line_id?: string
          qty_ordered?: number
          qty_received?: number
          remarks?: string | null
          shortage_excess?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "grn_lines_grn_id_fkey"
            columns: ["grn_id"]
            isOneToOne: false
            referencedRelation: "grn_header"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "grn_lines_item_id_fkey"
            columns: ["item_id"]
            isOneToOne: false
            referencedRelation: "items"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "grn_lines_lpo_line_id_fkey"
            columns: ["lpo_line_id"]
            isOneToOne: false
            referencedRelation: "lpo_lines"
            referencedColumns: ["id"]
          },
        ]
      }
      invoice_lines: {
        Row: {
          grn_line_id: string
          id: string
          invoice_id: string
          invoice_price: number
          item_id: string
          line_value: number | null
          lpo_price: number
          price_variance: number | null
          quantity: number
        }
        Insert: {
          grn_line_id: string
          id?: string
          invoice_id: string
          invoice_price?: number
          item_id: string
          line_value?: number | null
          lpo_price?: number
          price_variance?: number | null
          quantity: number
        }
        Update: {
          grn_line_id?: string
          id?: string
          invoice_id?: string
          invoice_price?: number
          item_id?: string
          line_value?: number | null
          lpo_price?: number
          price_variance?: number | null
          quantity?: number
        }
        Relationships: [
          {
            foreignKeyName: "invoice_lines_grn_line_id_fkey"
            columns: ["grn_line_id"]
            isOneToOne: false
            referencedRelation: "grn_lines"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "invoice_lines_invoice_id_fkey"
            columns: ["invoice_id"]
            isOneToOne: false
            referencedRelation: "invoices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "invoice_lines_item_id_fkey"
            columns: ["item_id"]
            isOneToOne: false
            referencedRelation: "items"
            referencedColumns: ["id"]
          },
        ]
      }
      invoices: {
        Row: {
          approved_at: string | null
          approver: string | null
          approver_name: string | null
          created_at: string
          grn_id: string
          id: string
          internal_number: string
          invoice_date: string
          invoice_number: string
          invoice_value: number
          lpo_id: string | null
          maker: string
          maker_name: string | null
          reject_reason: string | null
          status: Database["public"]["Enums"]["doc_status"]
          supplier_id: string
          total_value: number | null
          vat_amount: number
        }
        Insert: {
          approved_at?: string | null
          approver?: string | null
          approver_name?: string | null
          created_at?: string
          grn_id: string
          id?: string
          internal_number?: string
          invoice_date?: string
          invoice_number: string
          invoice_value?: number
          lpo_id?: string | null
          maker: string
          maker_name?: string | null
          reject_reason?: string | null
          status?: Database["public"]["Enums"]["doc_status"]
          supplier_id: string
          total_value?: number | null
          vat_amount?: number
        }
        Update: {
          approved_at?: string | null
          approver?: string | null
          approver_name?: string | null
          created_at?: string
          grn_id?: string
          id?: string
          internal_number?: string
          invoice_date?: string
          invoice_number?: string
          invoice_value?: number
          lpo_id?: string | null
          maker?: string
          maker_name?: string | null
          reject_reason?: string | null
          status?: Database["public"]["Enums"]["doc_status"]
          supplier_id?: string
          total_value?: number | null
          vat_amount?: number
        }
        Relationships: [
          {
            foreignKeyName: "invoices_grn_id_fkey"
            columns: ["grn_id"]
            isOneToOne: false
            referencedRelation: "grn_header"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "invoices_lpo_id_fkey"
            columns: ["lpo_id"]
            isOneToOne: false
            referencedRelation: "lpo_header"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "invoices_supplier_id_fkey"
            columns: ["supplier_id"]
            isOneToOne: false
            referencedRelation: "suppliers"
            referencedColumns: ["id"]
          },
        ]
      }
      items: {
        Row: {
          created_at: string
          id: string
          item_code: string
          item_description: string
          standard_price: number | null
          status: Database["public"]["Enums"]["master_status"]
          unit: string
        }
        Insert: {
          created_at?: string
          id?: string
          item_code: string
          item_description: string
          standard_price?: number | null
          status?: Database["public"]["Enums"]["master_status"]
          unit: string
        }
        Update: {
          created_at?: string
          id?: string
          item_code?: string
          item_description?: string
          standard_price?: number | null
          status?: Database["public"]["Enums"]["master_status"]
          unit?: string
        }
        Relationships: []
      }
      lpo_header: {
        Row: {
          approved_at: string | null
          approver: string | null
          approver_name: string | null
          created_at: string
          delivery_location: string | null
          department_id: string
          id: string
          lpo_date: string
          lpo_number: string
          maker: string
          maker_name: string | null
          payment_terms: string | null
          reject_reason: string | null
          remarks: string | null
          status: Database["public"]["Enums"]["doc_status"]
          supplier_id: string
          total_value: number
        }
        Insert: {
          approved_at?: string | null
          approver?: string | null
          approver_name?: string | null
          created_at?: string
          delivery_location?: string | null
          department_id: string
          id?: string
          lpo_date?: string
          lpo_number?: string
          maker: string
          maker_name?: string | null
          payment_terms?: string | null
          reject_reason?: string | null
          remarks?: string | null
          status?: Database["public"]["Enums"]["doc_status"]
          supplier_id: string
          total_value?: number
        }
        Update: {
          approved_at?: string | null
          approver?: string | null
          approver_name?: string | null
          created_at?: string
          delivery_location?: string | null
          department_id?: string
          id?: string
          lpo_date?: string
          lpo_number?: string
          maker?: string
          maker_name?: string | null
          payment_terms?: string | null
          reject_reason?: string | null
          remarks?: string | null
          status?: Database["public"]["Enums"]["doc_status"]
          supplier_id?: string
          total_value?: number
        }
        Relationships: [
          {
            foreignKeyName: "lpo_header_department_id_fkey"
            columns: ["department_id"]
            isOneToOne: false
            referencedRelation: "departments"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lpo_header_supplier_id_fkey"
            columns: ["supplier_id"]
            isOneToOne: false
            referencedRelation: "suppliers"
            referencedColumns: ["id"]
          },
        ]
      }
      lpo_lines: {
        Row: {
          id: string
          item_id: string
          line_value: number | null
          lpo_id: string
          quantity_ordered: number
          unit_price: number
        }
        Insert: {
          id?: string
          item_id: string
          line_value?: number | null
          lpo_id: string
          quantity_ordered: number
          unit_price: number
        }
        Update: {
          id?: string
          item_id?: string
          line_value?: number | null
          lpo_id?: string
          quantity_ordered?: number
          unit_price?: number
        }
        Relationships: [
          {
            foreignKeyName: "lpo_lines_item_id_fkey"
            columns: ["item_id"]
            isOneToOne: false
            referencedRelation: "items"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lpo_lines_lpo_id_fkey"
            columns: ["lpo_id"]
            isOneToOne: false
            referencedRelation: "lpo_header"
            referencedColumns: ["id"]
          },
        ]
      }
      profiles: {
        Row: {
          created_at: string
          email: string | null
          full_name: string
          id: string
        }
        Insert: {
          created_at?: string
          email?: string | null
          full_name?: string
          id: string
        }
        Update: {
          created_at?: string
          email?: string | null
          full_name?: string
          id?: string
        }
        Relationships: []
      }
      supplier_accounts: {
        Row: {
          contact_name: string
          created_at: string
          supplier_id: string
          user_id: string
        }
        Insert: {
          contact_name?: string
          created_at?: string
          supplier_id: string
          user_id: string
        }
        Update: {
          contact_name?: string
          created_at?: string
          supplier_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "supplier_accounts_supplier_id_fkey"
            columns: ["supplier_id"]
            isOneToOne: false
            referencedRelation: "suppliers"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "supplier_accounts_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: true
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      suppliers: {
        Row: {
          address: string | null
          approved_at: string | null
          approver: string | null
          approver_name: string | null
          contact_person: string | null
          created_at: string
          email: string | null
          id: string
          maker: string | null
          maker_name: string | null
          payment_terms: string | null
          phone: string | null
          status: Database["public"]["Enums"]["supplier_status"]
          supplier_code: string
          supplier_name: string
          vat_pin: string | null
        }
        Insert: {
          address?: string | null
          approved_at?: string | null
          approver?: string | null
          approver_name?: string | null
          contact_person?: string | null
          created_at?: string
          email?: string | null
          id?: string
          maker?: string | null
          maker_name?: string | null
          payment_terms?: string | null
          phone?: string | null
          status?: Database["public"]["Enums"]["supplier_status"]
          supplier_code: string
          supplier_name: string
          vat_pin?: string | null
        }
        Update: {
          address?: string | null
          approved_at?: string | null
          approver?: string | null
          approver_name?: string | null
          contact_person?: string | null
          created_at?: string
          email?: string | null
          id?: string
          maker?: string | null
          maker_name?: string | null
          payment_terms?: string | null
          phone?: string | null
          status?: Database["public"]["Enums"]["supplier_status"]
          supplier_code?: string
          supplier_name?: string
          vat_pin?: string | null
        }
        Relationships: []
      }
      user_roles: {
        Row: {
          created_at: string
          id: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
      is_internal_user: { Args: never; Returns: boolean }
      link_supplier_account: {
        Args: { p_email: string; p_supplier: string }
        Returns: undefined
      }
      next_document_number: { Args: { p_type: string }; Returns: string }
      owns_supplier: { Args: { p_supplier: string }; Returns: boolean }
    }
    Enums: {
      app_role:
        | "MAKER"
        | "APPROVER"
        | "ADMIN"
        | "STOREKEEPER"
        | "FINANCE_MAKER"
        | "FINANCE_APPROVER"
      doc_status: "DRAFT" | "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED"
      grn_receipt_status: "ACCEPTED" | "PARTIAL" | "REJECTED"
      item_condition: "OK" | "DAMAGED" | "WRONG_ITEM"
      master_status: "ACTIVE" | "INACTIVE"
      supplier_status: "PENDING" | "ACTIVE" | "INACTIVE"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: [
        "MAKER",
        "APPROVER",
        "ADMIN",
        "STOREKEEPER",
        "FINANCE_MAKER",
        "FINANCE_APPROVER",
      ],
      doc_status: ["DRAFT", "PENDING", "APPROVED", "REJECTED", "CANCELLED"],
      grn_receipt_status: ["ACCEPTED", "PARTIAL", "REJECTED"],
      item_condition: ["OK", "DAMAGED", "WRONG_ITEM"],
      master_status: ["ACTIVE", "INACTIVE"],
      supplier_status: ["PENDING", "ACTIVE", "INACTIVE"],
    },
  },
} as const
