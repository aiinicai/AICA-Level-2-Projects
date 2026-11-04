import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
const mocks = vi.hoisted(() => ({ save: vi.fn(), friends: [] as any[] }));
vi.mock("@/lib/firebase", () => ({ db: {} }));
vi.mock("@/lib/fairlyshareDb", () => ({ saveSettlement: mocks.save, saveExpense: vi.fn() }));
vi.mock("@tanstack/react-router", () => ({ useNavigate: () => vi.fn() }));
vi.mock("@/lib/app", () => ({
  useUser: () => ({ data: { id: "me", name: "You" } }),
  useFriends: () => ({ data: mocks.friends }),
  CURRENCIES: ["AED", "USD"],
  CATEGORIES: [],
  GROUP_TYPES: [],
  today: () => "2026-10-18",
  errMsg: String,
}));
vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ open, children }: any) => (open ? <div>{children}</div> : null),
  DialogContent: ({ children }: any) => <div>{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <h2>{children}</h2>,
  DialogFooter: ({ children }: any) => <div>{children}</div>,
}));
vi.mock("@/components/ui/select", () => ({
  Select: ({ value, onValueChange, children }: any) => (
    <select value={value} onChange={(e) => onValueChange(e.target.value)}>
      {children}
    </select>
  ),
  SelectTrigger: () => null,
  SelectValue: () => null,
  SelectContent: ({ children }: any) => <>{children}</>,
  SelectItem: ({ value, children }: any) => <option value={value}>{children}</option>,
}));
vi.mock("@/components/AppShell", () => ({ MemberAvatar: ({ name }: any) => <span>{name}</span> }));
import { SettleDialog, ExpenseDialog } from "@/components/Dialogs";
import { FriendDetailDialog } from "@/components/FriendDetailDialog";
const friend = {
  friendUser: { id: "sara" },
  friendship: { status: "accepted" },
  directExpenses: [
    {
      paid_by_uid: "me",
      currency: "AED",
      amount_units: 12000,
      splits: [
        { user_id: "me", amount_units: 6000 },
        { user_id: "sara", amount_units: 6000 },
      ],
    },
    {
      paid_by_uid: "me",
      currency: "USD",
      amount_units: 4000,
      splits: [
        { user_id: "me", amount_units: 2000 },
        { user_id: "sara", amount_units: 2000 },
      ],
    },
  ],
  directSettlements: [],
};
const group: any = {
  group: { id: "trip", name: "Trip", currency: "AED" },
  myMemberId: "member-me",
  members: [
    { id: "member-me", user_id: "me", name: "You" },
    { id: "member-sara", user_id: "sara", name: "Sara" },
    { id: "other", user_id: "other", name: "Omar" },
  ],
  expenses: [
    {
      id: "e1",
      paid_by_uid: "me",
      paid_by_member_id: "member-me",
      amount_units: 16000,
      currency: "AED",
      expense_splits: [
        { member_id: "member-me", amount_units: 8000 },
        { member_id: "member-sara", amount_units: 8000 },
      ],
    },
  ],
  settlements: [],
  netByCurrency: { AED: { "member-me": 98000, "member-sara": -8000, other: -90000 } },
};
function open(prefill: any = { currency: "AED", scope: "direct", from: "sara", to: "me" }) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <SettleDialog
        directFriend={{ id: "sara", name: "Sara", friendshipId: "friendship" }}
        sharedGroups={[group]}
        prefill={prefill}
        open
        onOpenChange={() => {}}
      />
    </QueryClientProvider>,
  );
}
describe("actual settlement form", () => {
  beforeEach(() => {
    cleanup();
    mocks.save.mockReset();
    mocks.save.mockResolvedValue(undefined);
    mocks.friends = [friend];
  });
  it("saves a partial direct payment using actual scope IDs and balance", async () => {
    open();
    fireEvent.change(screen.getByRole("spinbutton"), { target: { value: "40" } });
    expect(screen.getByText(/Sara will still owe you/)).toHaveTextContent("20.00");
    fireEvent.click(screen.getByRole("button", { name: "Record payment" }));
    await waitFor(() =>
      expect(mocks.save).toHaveBeenCalledWith(
        expect.objectContaining({
          groupId: null,
          friendshipId: "friendship",
          from_member_id: null,
          to_member_id: null,
          from_uid: "sara",
          to_uid: "me",
          amount_units: 4000,
          currency: "AED",
        }),
      ),
    );
  });
  it("maps group UID prefill to member IDs and uses bilateral group debt", async () => {
    open({ scope: "trip", currency: "AED", from: "sara", to: "me", cents: 8000 });
    expect(screen.getByRole("spinbutton")).toHaveValue(80);
    expect(screen.getByText(/Fully settled/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Record payment" }));
    await waitFor(() =>
      expect(mocks.save).toHaveBeenCalledWith(
        expect.objectContaining({
          groupId: "trip",
          friendshipId: null,
          from_member_id: "member-sara",
          to_member_id: "member-me",
          from_uid: "sara",
          to_uid: "me",
          amount_units: 8000,
        }),
      ),
    );
  });
  it("clears amount and uses the chosen currency balance", () => {
    open({ scope: "direct", currency: "AED", from: "sara", to: "me", cents: 6000 });
    fireEvent.change(screen.getAllByRole("combobox")[3]!, { target: { value: "USD" } });
    expect(screen.getByRole("spinbutton")).toHaveValue(null);
    fireEvent.change(screen.getByRole("spinbutton"), { target: { value: "20" } });
    expect(screen.getByText(/Fully settled/)).toBeInTheDocument();
  });
  it("clears an amount when changing scope and requires an explicit overpayment acknowledgement", () => {
    open({ scope: "direct", currency: "AED", from: "sara", to: "me", cents: 6000 });
    fireEvent.change(screen.getAllByRole("combobox")[0]!, { target: { value: "trip" } });
    expect(screen.getByRole("spinbutton")).toHaveValue(null);
    fireEvent.change(screen.getByRole("spinbutton"), { target: { value: "100" } });
    expect(screen.getByRole("button", { name: "Record payment" })).toBeDisabled();
    expect(mocks.save).not.toHaveBeenCalled();
  });
});

describe("ledger and expense rendering", () => {
  beforeEach(() => {
    cleanup();
    mocks.friends = [friend];
  });
  it("renders actual group row shape in the ledger and filters the backing activity", () => {
    const detailedFriend: any = {
      ...friend,
      friendUser: { id: "sara", display_name: "Sara", email: "" },
      directExpenses: friend.directExpenses.map((expense, index) => ({
        ...expense,
        id: `direct-${index}`,
        description: "Coffee",
        expense_date: "2026-10-18",
      })),
    };
    const detailedGroup = {
      ...group,
      expenses: group.expenses.map((expense: any) => ({
        ...expense,
        description: "Museum",
        expense_date: "2026-10-17",
      })),
    };
    render(
      <FriendDetailDialog
        friend={detailedFriend}
        groups={[detailedGroup]}
        myUid="me"
        open
        onOpenChange={() => {}}
        onSettleUp={() => {}}
        onAddDirectExpense={() => {}}
      />,
    );
    expect(screen.getByText("Museum")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Direct" }));
    expect(screen.queryByText("Museum")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Shared groups" }));
    expect(screen.getByText("Museum")).toBeInTheDocument();
    expect(screen.queryAllByText("Coffee")).toHaveLength(0);
  });
  it("renders new expense optional fields and accurate live split preview", () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ExpenseDialog
          directFriend={{ id: "sara", name: "Sara", friendshipId: "friendship" }}
          open
          onOpenChange={() => {}}
        />
      </QueryClientProvider>,
    );
    expect(screen.getByRole("button", { name: /More options/i })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("spinbutton"), { target: { value: "120" } });
    expect(screen.getByText(/Sara owes you/)).toHaveTextContent("60.00");
  });
});
