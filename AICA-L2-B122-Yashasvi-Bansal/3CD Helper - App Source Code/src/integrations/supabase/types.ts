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
    PostgrestVersion: "14.18"
  }
  public: {
    Tables: {
      activity_log: {
        Row: {
          action: string
          created_at: string
          details: Json | null
          entity: string | null
          entity_id: string | null
          firm_id: string
          id: number
          user_id: string | null
        }
        Insert: {
          action: string
          created_at?: string
          details?: Json | null
          entity?: string | null
          entity_id?: string | null
          firm_id: string
          id?: never
          user_id?: string | null
        }
        Update: {
          action?: string
          created_at?: string
          details?: Json | null
          entity?: string | null
          entity_id?: string | null
          firm_id?: string
          id?: never
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "activity_log_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      attachments: {
        Row: {
          created_at: string
          created_by: string | null
          engagement_id: string
          entity: string
          extracted: Json
          file_name: string
          firm_id: string
          id: string
          include: boolean
          kind: string | null
          party_name: string | null
          record_id: string | null
          remark: string | null
          storage_path: string
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          created_at?: string
          created_by?: string | null
          engagement_id: string
          entity: string
          extracted?: Json
          file_name: string
          firm_id: string
          id?: string
          include?: boolean
          kind?: string | null
          party_name?: string | null
          record_id?: string | null
          remark?: string | null
          storage_path: string
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          entity?: string
          extracted?: Json
          file_name?: string
          firm_id?: string
          id?: string
          include?: boolean
          kind?: string | null
          party_name?: string | null
          record_id?: string | null
          remark?: string | null
          storage_path?: string
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "attachments_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "attachments_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      cash_txns: {
        Row: {
          amount: number
          created_at: string
          created_by: string | null
          direction: string
          engagement_id: string
          firm_id: string
          id: string
          include: boolean
          mode: string
          nature: string | null
          normalized_name: string
          pan: string | null
          party_name: string
          remark: string | null
          row_no: number | null
          rule_6dd: string | null
          section: string
          txn_date: string
          updated_at: string
          updated_by: string | null
          upload_id: string | null
          voucher_no: string | null
        }
        Insert: {
          amount: number
          created_at?: string
          created_by?: string | null
          direction: string
          engagement_id: string
          firm_id: string
          id?: string
          include?: boolean
          mode?: string
          nature?: string | null
          normalized_name: string
          pan?: string | null
          party_name: string
          remark?: string | null
          row_no?: number | null
          rule_6dd?: string | null
          section?: string
          txn_date: string
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
          voucher_no?: string | null
        }
        Update: {
          amount?: number
          created_at?: string
          created_by?: string | null
          direction?: string
          engagement_id?: string
          firm_id?: string
          id?: string
          include?: boolean
          mode?: string
          nature?: string | null
          normalized_name?: string
          pan?: string | null
          party_name?: string
          remark?: string | null
          row_no?: number | null
          rule_6dd?: string | null
          section?: string
          txn_date?: string
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
          voucher_no?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "cash_txns_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "cash_txns_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "cash_txns_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      clients: {
        Row: {
          address: string | null
          archived: boolean
          contact_person: string | null
          created_at: string
          created_by: string | null
          email: string | null
          firm_id: string
          gstins: string[]
          id: string
          mobile: string | null
          name: string
          notes: string | null
          pan: string | null
          status: string
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          address?: string | null
          archived?: boolean
          contact_person?: string | null
          created_at?: string
          created_by?: string | null
          email?: string | null
          firm_id: string
          gstins?: string[]
          id?: string
          mobile?: string | null
          name: string
          notes?: string | null
          pan?: string | null
          status?: string
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          address?: string | null
          archived?: boolean
          contact_person?: string | null
          created_at?: string
          created_by?: string | null
          email?: string | null
          firm_id?: string
          gstins?: string[]
          id?: string
          mobile?: string | null
          name?: string
          notes?: string | null
          pan?: string | null
          status?: string
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "clients_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      column_mappings: {
        Row: {
          client_id: string | null
          created_at: string
          created_by: string | null
          firm_id: string
          id: string
          mapping: Json
          name: string
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          client_id?: string | null
          created_at?: string
          created_by?: string | null
          firm_id: string
          id?: string
          mapping: Json
          name: string
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          client_id?: string | null
          created_at?: string
          created_by?: string | null
          firm_id?: string
          id?: string
          mapping?: Json
          name?: string
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "column_mappings_client_id_fkey"
            columns: ["client_id"]
            isOneToOne: false
            referencedRelation: "clients"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "column_mappings_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      comments: {
        Row: {
          body: string
          created_at: string
          created_by: string | null
          engagement_id: string
          firm_id: string
          id: string
          row_id: string | null
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          body: string
          created_at?: string
          created_by?: string | null
          engagement_id: string
          firm_id: string
          id?: string
          row_id?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          body?: string
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          firm_id?: string
          id?: string
          row_id?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "comments_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "comments_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "comments_row_id_fkey"
            columns: ["row_id"]
            isOneToOne: false
            referencedRelation: "expense_rows"
            referencedColumns: ["id"]
          },
        ]
      }
      employee_contributions: {
        Row: {
          amount_paid: number
          amount_received: number
          challan_ref: string | null
          created_at: string
          created_by: string | null
          due_date: string | null
          engagement_id: string
          firm_id: string
          fund: string
          id: string
          include: boolean
          paid_date: string | null
          remark: string | null
          row_no: number | null
          source: string | null
          updated_at: string
          updated_by: string | null
          upload_id: string | null
          wage_month: string
        }
        Insert: {
          amount_paid?: number
          amount_received: number
          challan_ref?: string | null
          created_at?: string
          created_by?: string | null
          due_date?: string | null
          engagement_id: string
          firm_id: string
          fund: string
          id?: string
          include?: boolean
          paid_date?: string | null
          remark?: string | null
          row_no?: number | null
          source?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
          wage_month: string
        }
        Update: {
          amount_paid?: number
          amount_received?: number
          challan_ref?: string | null
          created_at?: string
          created_by?: string | null
          due_date?: string | null
          engagement_id?: string
          firm_id?: string
          fund?: string
          id?: string
          include?: boolean
          paid_date?: string | null
          remark?: string | null
          row_no?: number | null
          source?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
          wage_month?: string
        }
        Relationships: [
          {
            foreignKeyName: "employee_contributions_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "employee_contributions_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "employee_contributions_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      engagements: {
        Row: {
          assessment_year: string
          assigned_to: string | null
          clause_answers: Json
          client_id: string
          created_at: string
          created_by: string | null
          firm_id: string
          id: string
          locked: boolean
          msme_bank_rate: number | null
          pl_total_expenditure: number | null
          return_due_date: string | null
          reviewed_at: string | null
          reviewed_by: string | null
          status: string
          udin: string | null
          unlock_reason: string | null
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          assessment_year: string
          assigned_to?: string | null
          clause_answers?: Json
          client_id: string
          created_at?: string
          created_by?: string | null
          firm_id: string
          id?: string
          locked?: boolean
          msme_bank_rate?: number | null
          pl_total_expenditure?: number | null
          return_due_date?: string | null
          reviewed_at?: string | null
          reviewed_by?: string | null
          status?: string
          udin?: string | null
          unlock_reason?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          assessment_year?: string
          assigned_to?: string | null
          clause_answers?: Json
          client_id?: string
          created_at?: string
          created_by?: string | null
          firm_id?: string
          id?: string
          locked?: boolean
          msme_bank_rate?: number | null
          pl_total_expenditure?: number | null
          return_due_date?: string | null
          reviewed_at?: string | null
          reviewed_by?: string | null
          status?: string
          udin?: string | null
          unlock_reason?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "engagements_assigned_to_fkey"
            columns: ["assigned_to"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engagements_client_id_fkey"
            columns: ["client_id"]
            isOneToOne: false
            referencedRelation: "clients"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engagements_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engagements_reviewed_by_fkey"
            columns: ["reviewed_by"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      expense_rows: {
        Row: {
          amount: number
          category: string
          category_override: string | null
          created_at: string
          created_by: string | null
          effective_gstin: string | null
          engagement_id: string
          expense_head: string | null
          firm_id: string
          gstin: string | null
          gstin_status: string
          id: string
          include: boolean
          nature: string | null
          normalized_name: string
          party_name: string
          remark: string | null
          row_no: number | null
          txn_date: string | null
          updated_at: string
          updated_by: string | null
          upload_id: string | null
        }
        Insert: {
          amount?: number
          category?: string
          category_override?: string | null
          created_at?: string
          created_by?: string | null
          effective_gstin?: string | null
          engagement_id: string
          expense_head?: string | null
          firm_id: string
          gstin?: string | null
          gstin_status?: string
          id?: string
          include?: boolean
          nature?: string | null
          normalized_name: string
          party_name: string
          remark?: string | null
          row_no?: number | null
          txn_date?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Update: {
          amount?: number
          category?: string
          category_override?: string | null
          created_at?: string
          created_by?: string | null
          effective_gstin?: string | null
          engagement_id?: string
          expense_head?: string | null
          firm_id?: string
          gstin?: string | null
          gstin_status?: string
          id?: string
          include?: boolean
          nature?: string | null
          normalized_name?: string
          party_name?: string
          remark?: string | null
          row_no?: number | null
          txn_date?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "expense_rows_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "expense_rows_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "expense_rows_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      fa_blocks: {
        Row: {
          block_name: string
          book_depreciation: number | null
          created_at: string
          created_by: string | null
          engagement_id: string
          firm_id: string
          id: string
          include: boolean
          opening_wdv: number
          rate: number
          remark: string | null
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          block_name: string
          book_depreciation?: number | null
          created_at?: string
          created_by?: string | null
          engagement_id: string
          firm_id: string
          id?: string
          include?: boolean
          opening_wdv?: number
          rate: number
          remark?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          block_name?: string
          book_depreciation?: number | null
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          firm_id?: string
          id?: string
          include?: boolean
          opening_wdv?: number
          rate?: number
          remark?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "fa_blocks_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "fa_blocks_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      fa_ledger_map: {
        Row: {
          block_name: string | null
          created_at: string
          created_by: string | null
          engagement_id: string
          firm_id: string
          id: string
          include: boolean
          ledger_name: string
          remark: string | null
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          block_name?: string | null
          created_at?: string
          created_by?: string | null
          engagement_id: string
          firm_id: string
          id?: string
          include?: boolean
          ledger_name: string
          remark?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          block_name?: string | null
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          firm_id?: string
          id?: string
          include?: boolean
          ledger_name?: string
          remark?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "fa_ledger_map_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "fa_ledger_map_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      fa_movements: {
        Row: {
          additional_dep: boolean
          amount: number
          bill_date: string | null
          bill_no: string | null
          block_name: string
          cenvat: number
          created_at: string
          created_by: string | null
          description: string | null
          engagement_id: string
          firm_id: string
          forex: number
          gst_amount: number | null
          id: string
          include: boolean
          ledger_name: string | null
          movement: string
          remark: string | null
          row_no: number | null
          subsidy: number
          supplier: string | null
          txn_date: string | null
          updated_at: string
          updated_by: string | null
          upload_id: string | null
        }
        Insert: {
          additional_dep?: boolean
          amount?: number
          bill_date?: string | null
          bill_no?: string | null
          block_name: string
          cenvat?: number
          created_at?: string
          created_by?: string | null
          description?: string | null
          engagement_id: string
          firm_id: string
          forex?: number
          gst_amount?: number | null
          id?: string
          include?: boolean
          ledger_name?: string | null
          movement?: string
          remark?: string | null
          row_no?: number | null
          subsidy?: number
          supplier?: string | null
          txn_date?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Update: {
          additional_dep?: boolean
          amount?: number
          bill_date?: string | null
          bill_no?: string | null
          block_name?: string
          cenvat?: number
          created_at?: string
          created_by?: string | null
          description?: string | null
          engagement_id?: string
          firm_id?: string
          forex?: number
          gst_amount?: number | null
          id?: string
          include?: boolean
          ledger_name?: string | null
          movement?: string
          remark?: string | null
          row_no?: number | null
          subsidy?: number
          supplier?: string | null
          txn_date?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "fa_movements_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "fa_movements_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "fa_movements_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      firm_members: {
        Row: {
          created_at: string
          firm_id: string
          role: string
          user_id: string
        }
        Insert: {
          created_at?: string
          firm_id: string
          role?: string
          user_id: string
        }
        Update: {
          created_at?: string
          firm_id?: string
          role?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "firm_members_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "firm_members_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      firms: {
        Row: {
          address: string | null
          city: string | null
          created_at: string
          created_by: string | null
          email: string | null
          frn: string | null
          gstin: string | null
          id: string
          logo_url: string | null
          membership_no: string | null
          name: string
          pan: string | null
          partner_name: string | null
          phone: string | null
          pincode: string | null
          plan: string
          settings: Json
          state: string | null
          status: string
          trial_ends_at: string
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          address?: string | null
          city?: string | null
          created_at?: string
          created_by?: string | null
          email?: string | null
          frn?: string | null
          gstin?: string | null
          id?: string
          logo_url?: string | null
          membership_no?: string | null
          name: string
          pan?: string | null
          partner_name?: string | null
          phone?: string | null
          pincode?: string | null
          plan?: string
          settings?: Json
          state?: string | null
          status?: string
          trial_ends_at?: string
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          address?: string | null
          city?: string | null
          created_at?: string
          created_by?: string | null
          email?: string | null
          frn?: string | null
          gstin?: string | null
          id?: string
          logo_url?: string | null
          membership_no?: string | null
          name?: string
          pan?: string | null
          partner_name?: string | null
          phone?: string | null
          pincode?: string | null
          plan?: string
          settings?: Json
          state?: string | null
          status?: string
          trial_ends_at?: string
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: []
      }
      invitations: {
        Row: {
          accepted_at: string | null
          created_at: string
          email: string
          firm_id: string
          id: string
          invited_by: string | null
          role: string
          status: string
        }
        Insert: {
          accepted_at?: string | null
          created_at?: string
          email: string
          firm_id: string
          id?: string
          invited_by?: string | null
          role?: string
          status?: string
        }
        Update: {
          accepted_at?: string | null
          created_at?: string
          email?: string
          firm_id?: string
          id?: string
          invited_by?: string | null
          role?: string
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "invitations_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      loan_balances: {
        Row: {
          created_at: string
          created_by: string | null
          engagement_id: string
          firm_id: string
          id: string
          normalized_name: string
          opening_balance: number
          party_name: string
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          created_at?: string
          created_by?: string | null
          engagement_id: string
          firm_id: string
          id?: string
          normalized_name: string
          opening_balance?: number
          party_name: string
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          firm_id?: string
          id?: string
          normalized_name?: string
          opening_balance?: number
          party_name?: string
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "loan_balances_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "loan_balances_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      loan_txns: {
        Row: {
          amount: number
          created_at: string
          created_by: string | null
          engagement_id: string
          firm_id: string
          id: string
          include: boolean
          kind: string
          mode: string
          nature_code: string | null
          normalized_name: string
          pan: string | null
          party_name: string
          remark: string | null
          row_no: number | null
          txn_date: string | null
          updated_at: string
          updated_by: string | null
          upload_id: string | null
          voucher_no: string | null
        }
        Insert: {
          amount: number
          created_at?: string
          created_by?: string | null
          engagement_id: string
          firm_id: string
          id?: string
          include?: boolean
          kind: string
          mode?: string
          nature_code?: string | null
          normalized_name: string
          pan?: string | null
          party_name: string
          remark?: string | null
          row_no?: number | null
          txn_date?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
          voucher_no?: string | null
        }
        Update: {
          amount?: number
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          firm_id?: string
          id?: string
          include?: boolean
          kind?: string
          mode?: string
          nature_code?: string | null
          normalized_name?: string
          pan?: string | null
          party_name?: string
          remark?: string | null
          row_no?: number | null
          txn_date?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
          voucher_no?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "loan_txns_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "loan_txns_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "loan_txns_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      login_history: {
        Row: {
          created_at: string
          device: string | null
          id: number
          user_id: string
        }
        Insert: {
          created_at?: string
          device?: string | null
          id?: never
          user_id?: string
        }
        Update: {
          created_at?: string
          device?: string | null
          id?: never
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "login_history_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      msme_bills: {
        Row: {
          acceptance_date: string | null
          amount: number
          bill_date: string
          bill_no: string | null
          created_at: string
          created_by: string | null
          engagement_id: string
          firm_id: string
          id: string
          include: boolean
          normalized_name: string
          paid_amount: number
          paid_date: string | null
          party_name: string
          remark: string | null
          row_no: number | null
          updated_at: string
          updated_by: string | null
          upload_id: string | null
        }
        Insert: {
          acceptance_date?: string | null
          amount: number
          bill_date: string
          bill_no?: string | null
          created_at?: string
          created_by?: string | null
          engagement_id: string
          firm_id: string
          id?: string
          include?: boolean
          normalized_name: string
          paid_amount?: number
          paid_date?: string | null
          party_name: string
          remark?: string | null
          row_no?: number | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Update: {
          acceptance_date?: string | null
          amount?: number
          bill_date?: string
          bill_no?: string | null
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          firm_id?: string
          id?: string
          include?: boolean
          normalized_name?: string
          paid_amount?: number
          paid_date?: string | null
          party_name?: string
          remark?: string | null
          row_no?: number | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "msme_bills_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "msme_bills_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "msme_bills_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      party_master: {
        Row: {
          address: string | null
          agreed_credit_days: number | null
          client_id: string
          created_at: string
          created_by: string | null
          firm_id: string
          gstin: string | null
          id: string
          is_composition: boolean
          is_exempt: boolean
          is_exempt_lender: boolean
          is_related: boolean
          is_transporter: boolean
          msme_activity: string | null
          msme_category: string | null
          msme_trader: boolean
          normalized_name: string
          pan: string | null
          party_name: string
          relationship: string | null
          udyam_no: string | null
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          address?: string | null
          agreed_credit_days?: number | null
          client_id: string
          created_at?: string
          created_by?: string | null
          firm_id: string
          gstin?: string | null
          id?: string
          is_composition?: boolean
          is_exempt?: boolean
          is_exempt_lender?: boolean
          is_related?: boolean
          is_transporter?: boolean
          msme_activity?: string | null
          msme_category?: string | null
          msme_trader?: boolean
          normalized_name: string
          pan?: string | null
          party_name: string
          relationship?: string | null
          udyam_no?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          address?: string | null
          agreed_credit_days?: number | null
          client_id?: string
          created_at?: string
          created_by?: string | null
          firm_id?: string
          gstin?: string | null
          id?: string
          is_composition?: boolean
          is_exempt?: boolean
          is_exempt_lender?: boolean
          is_related?: boolean
          is_transporter?: boolean
          msme_activity?: string | null
          msme_category?: string | null
          msme_trader?: boolean
          normalized_name?: string
          pan?: string | null
          party_name?: string
          relationship?: string | null
          udyam_no?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "party_master_client_id_fkey"
            columns: ["client_id"]
            isOneToOne: false
            referencedRelation: "clients"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "party_master_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      profiles: {
        Row: {
          created_at: string
          email: string | null
          full_name: string | null
          id: string
          mobile: string | null
          updated_at: string
          username: string | null
        }
        Insert: {
          created_at?: string
          email?: string | null
          full_name?: string | null
          id: string
          mobile?: string | null
          updated_at?: string
          username?: string | null
        }
        Update: {
          created_at?: string
          email?: string | null
          full_name?: string | null
          id?: string
          mobile?: string | null
          updated_at?: string
          username?: string | null
        }
        Relationships: []
      }
      related_txns: {
        Row: {
          amount: number
          created_at: string
          created_by: string | null
          engagement_id: string
          firm_id: string
          id: string
          include: boolean
          nature: string | null
          normalized_name: string
          pan: string | null
          party_name: string
          relationship: string | null
          remark: string | null
          row_no: number | null
          source: string
          updated_at: string
          updated_by: string | null
          upload_id: string | null
        }
        Insert: {
          amount?: number
          created_at?: string
          created_by?: string | null
          engagement_id: string
          firm_id: string
          id?: string
          include?: boolean
          nature?: string | null
          normalized_name: string
          pan?: string | null
          party_name: string
          relationship?: string | null
          remark?: string | null
          row_no?: number | null
          source?: string
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Update: {
          amount?: number
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          firm_id?: string
          id?: string
          include?: boolean
          nature?: string | null
          normalized_name?: string
          pan?: string | null
          party_name?: string
          relationship?: string | null
          remark?: string | null
          row_no?: number | null
          source?: string
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "related_txns_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "related_txns_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "related_txns_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      row_history: {
        Row: {
          changed_at: string
          changed_by: string | null
          field: string
          firm_id: string
          id: number
          new_value: string | null
          old_value: string | null
          record_id: string
          table_name: string
        }
        Insert: {
          changed_at?: string
          changed_by?: string | null
          field: string
          firm_id: string
          id?: never
          new_value?: string | null
          old_value?: string | null
          record_id: string
          table_name: string
        }
        Update: {
          changed_at?: string
          changed_by?: string | null
          field?: string
          firm_id?: string
          id?: never
          new_value?: string | null
          old_value?: string | null
          record_id?: string
          table_name?: string
        }
        Relationships: [
          {
            foreignKeyName: "row_history_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      statutory_dues: {
        Row: {
          amount: number
          created_at: string
          created_by: string | null
          engagement_id: string
          firm_id: string
          id: string
          include: boolean
          nature: string
          paid_amount: number
          paid_date: string | null
          pre_existing: boolean
          remark: string | null
          row_no: number | null
          section_clause: string
          updated_at: string
          updated_by: string | null
          upload_id: string | null
        }
        Insert: {
          amount: number
          created_at?: string
          created_by?: string | null
          engagement_id: string
          firm_id: string
          id?: string
          include?: boolean
          nature: string
          paid_amount?: number
          paid_date?: string | null
          pre_existing?: boolean
          remark?: string | null
          row_no?: number | null
          section_clause: string
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Update: {
          amount?: number
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          firm_id?: string
          id?: string
          include?: boolean
          nature?: string
          paid_amount?: number
          paid_date?: string | null
          pre_existing?: boolean
          remark?: string | null
          row_no?: number | null
          section_clause?: string
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "statutory_dues_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "statutory_dues_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "statutory_dues_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      stock_items: {
        Row: {
          category: string
          closing_qty: number
          closing_value: number | null
          consumption_qty: number
          created_at: string
          created_by: string | null
          engagement_id: string
          firm_id: string
          id: string
          include: boolean
          item_name: string
          manufactured_qty: number
          opening_qty: number
          purchase_qty: number
          remark: string | null
          row_no: number | null
          sales_qty: number
          shortage_qty: number
          unit: string | null
          updated_at: string
          updated_by: string | null
          upload_id: string | null
        }
        Insert: {
          category?: string
          closing_qty?: number
          closing_value?: number | null
          consumption_qty?: number
          created_at?: string
          created_by?: string | null
          engagement_id: string
          firm_id: string
          id?: string
          include?: boolean
          item_name: string
          manufactured_qty?: number
          opening_qty?: number
          purchase_qty?: number
          remark?: string | null
          row_no?: number | null
          sales_qty?: number
          shortage_qty?: number
          unit?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Update: {
          category?: string
          closing_qty?: number
          closing_value?: number | null
          consumption_qty?: number
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          firm_id?: string
          id?: string
          include?: boolean
          item_name?: string
          manufactured_qty?: number
          opening_qty?: number
          purchase_qty?: number
          remark?: string | null
          row_no?: number | null
          sales_qty?: number
          shortage_qty?: number
          unit?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "stock_items_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "stock_items_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "stock_items_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      tds_declarations: {
        Row: {
          cert_no: string | null
          created_at: string
          created_by: string | null
          decl_type: string
          engagement_id: string
          file_name: string | null
          firm_id: string
          id: string
          include: boolean
          limit_amount: number | null
          normalized_name: string
          pan: string | null
          party_name: string
          rate: number | null
          received_date: string | null
          remark: string | null
          section: string | null
          storage_path: string | null
          updated_at: string
          updated_by: string | null
          valid_from: string | null
          valid_to: string | null
          vehicles: number | null
          verified: boolean
        }
        Insert: {
          cert_no?: string | null
          created_at?: string
          created_by?: string | null
          decl_type: string
          engagement_id: string
          file_name?: string | null
          firm_id: string
          id?: string
          include?: boolean
          limit_amount?: number | null
          normalized_name: string
          pan?: string | null
          party_name: string
          rate?: number | null
          received_date?: string | null
          remark?: string | null
          section?: string | null
          storage_path?: string | null
          updated_at?: string
          updated_by?: string | null
          valid_from?: string | null
          valid_to?: string | null
          vehicles?: number | null
          verified?: boolean
        }
        Update: {
          cert_no?: string | null
          created_at?: string
          created_by?: string | null
          decl_type?: string
          engagement_id?: string
          file_name?: string | null
          firm_id?: string
          id?: string
          include?: boolean
          limit_amount?: number | null
          normalized_name?: string
          pan?: string | null
          party_name?: string
          rate?: number | null
          received_date?: string | null
          remark?: string | null
          section?: string | null
          storage_path?: string | null
          updated_at?: string
          updated_by?: string | null
          valid_from?: string | null
          valid_to?: string | null
          vehicles?: number | null
          verified?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "tds_declarations_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "tds_declarations_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      tds_deductions: {
        Row: {
          amount_paid: number
          created_at: string
          created_by: string | null
          deduction_date: string | null
          deposit_date: string | null
          engagement_id: string
          firm_id: string
          form_type: string | null
          id: string
          include: boolean
          lower_rate: boolean
          normalized_name: string
          pan: string | null
          party_name: string
          remark: string | null
          row_no: number | null
          section: string
          tan: string | null
          tds_amount: number
          txn_date: string | null
          updated_at: string
          updated_by: string | null
          upload_id: string | null
        }
        Insert: {
          amount_paid?: number
          created_at?: string
          created_by?: string | null
          deduction_date?: string | null
          deposit_date?: string | null
          engagement_id: string
          firm_id: string
          form_type?: string | null
          id?: string
          include?: boolean
          lower_rate?: boolean
          normalized_name: string
          pan?: string | null
          party_name: string
          remark?: string | null
          row_no?: number | null
          section: string
          tan?: string | null
          tds_amount?: number
          txn_date?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Update: {
          amount_paid?: number
          created_at?: string
          created_by?: string | null
          deduction_date?: string | null
          deposit_date?: string | null
          engagement_id?: string
          firm_id?: string
          form_type?: string | null
          id?: string
          include?: boolean
          lower_rate?: boolean
          normalized_name?: string
          pan?: string | null
          party_name?: string
          remark?: string | null
          row_no?: number | null
          section?: string
          tan?: string | null
          tds_amount?: number
          txn_date?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "tds_deductions_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "tds_deductions_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "tds_deductions_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      tds_payments: {
        Row: {
          amount: number
          created_at: string
          created_by: string | null
          engagement_id: string
          firm_id: string
          id: string
          include: boolean
          nature: string | null
          normalized_name: string
          pan: string | null
          party_name: string
          remark: string | null
          resident: boolean
          row_no: number | null
          section: string
          tds_required: string
          txn_date: string | null
          updated_at: string
          updated_by: string | null
          upload_id: string | null
        }
        Insert: {
          amount?: number
          created_at?: string
          created_by?: string | null
          engagement_id: string
          firm_id: string
          id?: string
          include?: boolean
          nature?: string | null
          normalized_name: string
          pan?: string | null
          party_name: string
          remark?: string | null
          resident?: boolean
          row_no?: number | null
          section: string
          tds_required?: string
          txn_date?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Update: {
          amount?: number
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          firm_id?: string
          id?: string
          include?: boolean
          nature?: string | null
          normalized_name?: string
          pan?: string | null
          party_name?: string
          remark?: string | null
          resident?: boolean
          row_no?: number | null
          section?: string
          tds_required?: string
          txn_date?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "tds_payments_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "tds_payments_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "tds_payments_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      tds_returns: {
        Row: {
          all_info: string
          created_at: string
          created_by: string | null
          due_date: string | null
          engagement_id: string
          filed_date: string | null
          firm_id: string
          form_type: string
          id: string
          include: boolean
          interest_paid: number
          interest_paid_date: string | null
          quarter: string
          remark: string | null
          row_no: number | null
          tan: string | null
          updated_at: string
          updated_by: string | null
          upload_id: string | null
        }
        Insert: {
          all_info?: string
          created_at?: string
          created_by?: string | null
          due_date?: string | null
          engagement_id: string
          filed_date?: string | null
          firm_id: string
          form_type: string
          id?: string
          include?: boolean
          interest_paid?: number
          interest_paid_date?: string | null
          quarter: string
          remark?: string | null
          row_no?: number | null
          tan?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Update: {
          all_info?: string
          created_at?: string
          created_by?: string | null
          due_date?: string | null
          engagement_id?: string
          filed_date?: string | null
          firm_id?: string
          form_type?: string
          id?: string
          include?: boolean
          interest_paid?: number
          interest_paid_date?: string | null
          quarter?: string
          remark?: string | null
          row_no?: number | null
          tan?: string | null
          updated_at?: string
          updated_by?: string | null
          upload_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "tds_returns_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "tds_returns_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "tds_returns_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      upload_links: {
        Row: {
          created_at: string
          created_by: string | null
          deliver_to: string
          engagement_id: string
          expires_at: string
          firm_id: string
          id: string
          message: string | null
          module: string
          revoked_at: string | null
          token: string
        }
        Insert: {
          created_at?: string
          created_by?: string | null
          deliver_to?: string
          engagement_id: string
          expires_at?: string
          firm_id: string
          id?: string
          message?: string | null
          module?: string
          revoked_at?: string | null
          token?: string
        }
        Update: {
          created_at?: string
          created_by?: string | null
          deliver_to?: string
          engagement_id?: string
          expires_at?: string
          firm_id?: string
          id?: string
          message?: string | null
          module?: string
          revoked_at?: string | null
          token?: string
        }
        Relationships: [
          {
            foreignKeyName: "upload_links_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "upload_links_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      uploads: {
        Row: {
          created_at: string
          created_by: string | null
          engagement_id: string
          file_name: string
          file_size: number | null
          firm_id: string
          id: string
          module: string
          row_count: number
          software_detected: string | null
          source: string
          storage_path: string | null
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          created_at?: string
          created_by?: string | null
          engagement_id: string
          file_name: string
          file_size?: number | null
          firm_id: string
          id?: string
          module?: string
          row_count?: number
          software_detected?: string | null
          source?: string
          storage_path?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          created_at?: string
          created_by?: string | null
          engagement_id?: string
          file_name?: string
          file_size?: number | null
          firm_id?: string
          id?: string
          module?: string
          row_count?: number
          software_detected?: string | null
          source?: string
          storage_path?: string | null
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "uploads_engagement_id_fkey"
            columns: ["engagement_id"]
            isOneToOne: false
            referencedRelation: "engagements"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "uploads_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      accept_my_invitations: { Args: never; Returns: number }
      can_edit_firm: { Args: { p_firm: string }; Returns: boolean }
      clause44_exceptions: {
        Args: { p_eng: string }
        Returns: {
          amount: number
          detail: string
          kind: string
          normalized_name: string
          party_name: string
          row_count: number
        }[]
      }
      clause44_head_summary: {
        Args: { p_eng: string }
        Returns: {
          excluded_amount: number
          excluded_count: number
          expense_head: string
          included_amount: number
          row_count: number
          total: number
        }[]
      }
      clause44_party_summary: {
        Args: { p_eng: string }
        Returns: {
          category: string
          excluded_amount: number
          gstin: string
          gstin_status: string
          gstin_variants: number
          included_amount: number
          normalized_name: string
          party_name: string
          row_count: number
        }[]
      }
      clause44_summary: {
        Args: { p_eng: string }
        Returns: {
          composition: number
          excluded: number
          excluded_count: number
          exempt: number
          invalid_gstin_count: number
          negative_count: number
          other_registered: number
          party_count: number
          registered_total: number
          reported_total: number
          row_count: number
          total_uploaded: number
          unregistered: number
        }[]
      }
      client_link_info: { Args: { p_token: string }; Returns: Json }
      client_link_ok: {
        Args: { p_eng: string; p_firm: string; p_token: string }
        Returns: boolean
      }
      client_link_register: {
        Args: {
          p_file_name: string
          p_path: string
          p_size: number
          p_token: string
        }
        Returns: undefined
      }
      create_firm: {
        Args: {
          p_address?: string
          p_city?: string
          p_email?: string
          p_frn?: string
          p_gstin?: string
          p_membership_no?: string
          p_name: string
          p_partner_name?: string
          p_phone?: string
          p_state?: string
        }
        Returns: string
      }
      email_for_login: { Args: { p_login: string }; Returns: string }
      engagement_editable: { Args: { p_eng: string }; Returns: boolean }
      firm_dashboard: { Args: { p_firm: string }; Returns: Json }
      firm_role: { Args: { p_firm: string }; Returns: string }
      firm_team: {
        Args: { p_firm: string }
        Returns: {
          email: string
          full_name: string
          joined_at: string
          role: string
          user_id: string
        }[]
      }
      gstin_is_valid: { Args: { p: string }; Returns: boolean }
      is_firm_admin: { Args: { p_firm: string }; Returns: boolean }
      is_firm_member: { Args: { p_firm: string }; Returns: boolean }
      merge_parties: {
        Args: { p_client: string; p_from: string; p_into: string }
        Returns: number
      }
      reclassify_engagement: { Args: { p_eng: string }; Returns: number }
      set_my_username: { Args: { p_username: string }; Returns: string }
      shares_firm_with: { Args: { p_user: string }; Returns: boolean }
      upsert_parties: {
        Args: { p_client: string; p_parties: Json }
        Returns: number
      }
    }
    Enums: {
      [_ in never]: never
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
    Enums: {},
  },
} as const
