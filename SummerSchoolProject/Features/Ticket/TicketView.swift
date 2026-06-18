//
//  TicketView.swift
//  SummerSchoolProject
//

import SwiftUI

struct TicketView: View {
    @StateObject private var viewModel = TicketViewModel()

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Билет")
                .task { await viewModel.load() }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingView()
        case .loaded(let ticket):
            ticketCard(ticket)
        case .failed(let error):
            ErrorStateView(error: error) {
                Task { await viewModel.load() }
            }
        }
    }

    private func ticketCard(_ ticket: Ticket) -> some View {
        VStack(spacing: 20) {
            if let qr = QRCodeGenerator.image(from: ticket.qrPayload) {
                Image(uiImage: qr)
                    .interpolation(.none)
                    .resizable()
                    .scaledToFit()
                    .frame(width: 220, height: 220)
            } else {
                Text("Не удалось построить QR-код")
                    .foregroundStyle(.secondary)
            }

            VStack(spacing: 8) {
                Text(ticket.passengerName)
                    .font(.title2.bold())
                HStack(spacing: 24) {
                    info("Рейс", ticket.flightNumber)
                    info("Место", ticket.seat)
                    info("Выход", ticket.gate)
                }
            }
        }
        .padding()
    }

    private func info(_ title: String, _ value: String) -> some View {
        VStack(spacing: 2) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.headline)
        }
    }
}
