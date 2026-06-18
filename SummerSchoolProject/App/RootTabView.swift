//
//  RootTabView.swift
//  SummerSchoolProject
//

import SwiftUI

struct RootTabView: View {
    var body: some View {
        TabView {
            FeedView()
                .tabItem { Label("Лента", systemImage: "list.bullet") }

            TicketView()
                .tabItem { Label("Билет", systemImage: "qrcode") }

            BalanceView()
                .tabItem { Label("Баланс", systemImage: "wallet.pass") }

            SettingsView()
                .tabItem { Label("Настройки", systemImage: "gearshape") }
        }
    }
}
