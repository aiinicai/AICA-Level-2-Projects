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
      accounts: {
        Row: {
          anthropic_key_encrypted: string | null
          anthropic_key_last4: string | null
          challenge_level: string
          claude_model: string
          created_at: string
          device_id: string | null
          device_secret_hash: string | null
          email: string | null
          feedback_style: string
          id: string
          input_language: string
          monthly_credit_remaining_usd: number
          monthly_credit_resets_at: string
          output_language: string
          purchased_credit_balance_usd: number
          sarvam_key_encrypted: string | null
          sarvam_key_last4: string | null
          updated_at: string
          user_id: string | null
          welcome_credit_remaining_usd: number
        }
        Insert: {
          anthropic_key_encrypted?: string | null
          anthropic_key_last4?: string | null
          challenge_level?: string
          claude_model?: string
          created_at?: string
          device_id?: string | null
          device_secret_hash?: string | null
          email?: string | null
          feedback_style?: string
          id?: string
          input_language?: string
          monthly_credit_remaining_usd?: number
          monthly_credit_resets_at?: string
          output_language?: string
          purchased_credit_balance_usd?: number
          sarvam_key_encrypted?: string | null
          sarvam_key_last4?: string | null
          updated_at?: string
          user_id?: string | null
          welcome_credit_remaining_usd?: number
        }
        Update: {
          anthropic_key_encrypted?: string | null
          anthropic_key_last4?: string | null
          challenge_level?: string
          claude_model?: string
          created_at?: string
          device_id?: string | null
          device_secret_hash?: string | null
          email?: string | null
          feedback_style?: string
          id?: string
          input_language?: string
          monthly_credit_remaining_usd?: number
          monthly_credit_resets_at?: string
          output_language?: string
          purchased_credit_balance_usd?: number
          sarvam_key_encrypted?: string | null
          sarvam_key_last4?: string | null
          updated_at?: string
          user_id?: string | null
          welcome_credit_remaining_usd?: number
        }
        Relationships: []
      }
      conversation_jobs: {
        Row: {
          account_id: string | null
          analysis: Json | null
          confirmed_speaker: string | null
          created_at: string
          error: string | null
          goal: string
          guessed_speaker: string | null
          id: string
          inferred_persona: string | null
          persona: string
          sarvam_job_id: string | null
          session_type: string | null
          speaker_samples: Json
          stage_message: string | null
          status: string
          transcript: string | null
          updated_at: string
          user_id: string | null
        }
        Insert: {
          account_id?: string | null
          analysis?: Json | null
          confirmed_speaker?: string | null
          created_at?: string
          error?: string | null
          goal?: string
          guessed_speaker?: string | null
          id?: string
          inferred_persona?: string | null
          persona?: string
          sarvam_job_id?: string | null
          session_type?: string | null
          speaker_samples?: Json
          stage_message?: string | null
          status?: string
          transcript?: string | null
          updated_at?: string
          user_id?: string | null
        }
        Update: {
          account_id?: string | null
          analysis?: Json | null
          confirmed_speaker?: string | null
          created_at?: string
          error?: string | null
          goal?: string
          guessed_speaker?: string | null
          id?: string
          inferred_persona?: string | null
          persona?: string
          sarvam_job_id?: string | null
          session_type?: string | null
          speaker_samples?: Json
          stage_message?: string | null
          status?: string
          transcript?: string | null
          updated_at?: string
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "conversation_jobs_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
            referencedColumns: ["id"]
          },
        ]
      }
      credit_transactions: {
        Row: {
          account_id: string
          amount_usd: number
          created_at: string
          id: string
          payment_ref: string | null
          pool: string | null
          session_type: string | null
          type: string
        }
        Insert: {
          account_id: string
          amount_usd: number
          created_at?: string
          id?: string
          payment_ref?: string | null
          pool?: string | null
          session_type?: string | null
          type: string
        }
        Update: {
          account_id?: string
          amount_usd?: number
          created_at?: string
          id?: string
          payment_ref?: string | null
          pool?: string | null
          session_type?: string | null
          type?: string
        }
        Relationships: [
          {
            foreignKeyName: "credit_transactions_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
            referencedColumns: ["id"]
          },
        ]
      }
      payments: {
        Row: {
          account_id: string | null
          admin_note: string | null
          amount_inr: number
          created_at: string
          credit_usd: number
          id: string
          months: number
          reference: string | null
          reviewed_at: string | null
          reviewed_by: string | null
          screenshot_path: string | null
          status: string
          upi_id: string
          user_id: string | null
        }
        Insert: {
          account_id?: string | null
          admin_note?: string | null
          amount_inr?: number
          created_at?: string
          credit_usd?: number
          id?: string
          months?: number
          reference?: string | null
          reviewed_at?: string | null
          reviewed_by?: string | null
          screenshot_path?: string | null
          status?: string
          upi_id?: string
          user_id?: string | null
        }
        Update: {
          account_id?: string | null
          admin_note?: string | null
          amount_inr?: number
          created_at?: string
          credit_usd?: number
          id?: string
          months?: number
          reference?: string | null
          reviewed_at?: string | null
          reviewed_by?: string | null
          screenshot_path?: string | null
          status?: string
          upi_id?: string
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "payments_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
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
          paid_until: string | null
          trial_ends_at: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          email?: string | null
          full_name?: string | null
          id: string
          paid_until?: string | null
          trial_ends_at?: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          email?: string | null
          full_name?: string | null
          id?: string
          paid_until?: string | null
          trial_ends_at?: string
          updated_at?: string
        }
        Relationships: []
      }
      reflection_messages: {
        Row: {
          account_id: string | null
          content: string
          created_at: string
          id: string
          role: string
          session_id: string
          user_id: string | null
        }
        Insert: {
          account_id?: string | null
          content: string
          created_at?: string
          id?: string
          role: string
          session_id: string
          user_id?: string | null
        }
        Update: {
          account_id?: string | null
          content?: string
          created_at?: string
          id?: string
          role?: string
          session_id?: string
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "reflection_messages_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "reflection_messages_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "reflection_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      reflection_sessions: {
        Row: {
          account_id: string | null
          created_at: string
          ended_at: string | null
          id: string
          label: string
          session_type: string | null
          updated_at: string
          user_id: string | null
        }
        Insert: {
          account_id?: string | null
          created_at?: string
          ended_at?: string | null
          id?: string
          label?: string
          session_type?: string | null
          updated_at?: string
          user_id?: string | null
        }
        Update: {
          account_id?: string | null
          created_at?: string
          ended_at?: string | null
          id?: string
          label?: string
          session_type?: string | null
          updated_at?: string
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "reflection_sessions_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
            referencedColumns: ["id"]
          },
        ]
      }
      reflection_themes: {
        Row: {
          recent_themes: Json
          updated_at: string
          user_id: string
        }
        Insert: {
          recent_themes?: Json
          updated_at?: string
          user_id: string
        }
        Update: {
          recent_themes?: Json
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      user_ai_settings: {
        Row: {
          anthropic_key_last4: string | null
          challenge_level: string
          claude_model: string
          created_at: string
          feedback_style: string
          input_language: string
          output_language: string
          sarvam_key_last4: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          anthropic_key_last4?: string | null
          challenge_level?: string
          claude_model?: string
          created_at?: string
          feedback_style?: string
          input_language?: string
          output_language?: string
          sarvam_key_last4?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          anthropic_key_last4?: string | null
          challenge_level?: string
          claude_model?: string
          created_at?: string
          feedback_style?: string
          input_language?: string
          output_language?: string
          sarvam_key_last4?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      user_api_keys: {
        Row: {
          anthropic_key_encrypted: string | null
          created_at: string
          sarvam_key_encrypted: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          anthropic_key_encrypted?: string | null
          created_at?: string
          sarvam_key_encrypted?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          anthropic_key_encrypted?: string | null
          created_at?: string
          sarvam_key_encrypted?: string | null
          updated_at?: string
          user_id?: string
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
    }
    Enums: {
      app_role: "admin" | "user"
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
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
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
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
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
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
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
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
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
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
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
      app_role: ["admin", "user"],
    },
  },
} as const
