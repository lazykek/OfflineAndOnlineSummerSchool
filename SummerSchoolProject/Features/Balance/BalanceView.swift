//
//  BalanceView.swift
//  SummerSchoolProject
//

import SwiftUI

struct BalanceView: View {
    @StateObject private var viewModel = BalanceViewModel()

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Баланс")
                .task { await viewModel.load() }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingView()
        case .loaded(let balance):
            balanceCard(balance)
        case .failed(let error):
            ErrorStateView(error: error) {
                Task { await viewModel.load() }
            }
        }
    }

    private func balanceCard(_ balance: Balance) -> some View {
        VStack(spacing: 24) {
            VStack(spacing: 6) {
                Text("Доступно")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text(balance.formattedAmount)
                    .font(.system(size: 44, weight: .bold, design: .rounded))
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 32)
            .background(.tint.opacity(0.1), in: RoundedRectangle(cornerRadius: 20))

            VStack(alignment: .leading, spacing: 12) {
                row("Владелец", balance.holderName)
                row("Email", balance.email)
                row("Город", balance.city)
            }
        }
        .padding()
        .frame(maxHeight: .infinity, alignment: .top)
    }

    private func row(_ title: String, _ value: String) -> some View {
        HStack {
            Text(title)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .fontWeight(.medium)
        }
    }
}
