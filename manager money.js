let currentUsername = "";
let isRegisterMode = false;

function toggleAuthMode() {
    isRegisterMode = !isRegisterMode;
    document.getElementById("auth-title").innerText = isRegisterMode ? "Đăng Ký" : "Đăng Nhập";
    document.getElementById("auth-btn").innerText = isRegisterMode ? "Đăng Ký Ngay" : "Đăng Nhập";
    document.getElementById("auth-switch").innerText = isRegisterMode ? "Đã có tài khoản? Đăng nhập" : "Chưa có tài khoản? Đăng ký ngay";
}

async function handleAuth() {
    const user = document.getElementById("auth-user").value.trim();
    const pass = document.getElementById("auth-pass").value.trim();

    if (!user || !pass) {
        alert("Vui lòng điền đầy đủ thông tin!");
        return;
    }

    const endpoint = isRegisterMode ? "/api/register" : "/api/login";

    try {
        const response = await fetch(`https://manager-money.onrender.com${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: user, password: pass })
        });

        const data = await response.json();

        if (!data.success) {
            alert(data.message);
            return;
        }

        if (isRegisterMode) {
            alert("Đăng ký thành công! Hãy đăng nhập.");
            toggleAuthMode();
            return;
        }

        currentUsername = user;
        document.getElementById("auth-modal").style.display = "none";
        document.getElementById("logout-btn").style.display = "block";

        if (data.is_new) {
            document.getElementById("welcome-modal").style.display = "flex";
        } else {
            updateDashboard(data.so_du);
            renderHistory(data.history);
        }

    } catch (error) {
        alert("Lỗi kết nối máy chủ!");
    }
}

async function xacNhanSoDu() {
    const initCash = parseInt(document.getElementById("init-cash").value) || 0;
    const initBank = parseInt(document.getElementById("init-bank").value) || 0;

    const response = await fetch("https://manager-money.onrender.com/api/init", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: currentUsername, tien_mat: initCash, tien_tk: initBank })
    });

    const data = await response.json();
    updateDashboard(data.so_du);
    renderHistory(data.history);
    document.getElementById("welcome-modal").style.display = "none";
}

async function sendMessage() {
    const inputField = document.getElementById("chat-input");
    const chatHistory = document.getElementById("chat-history");
    const messageText = inputField.value.trim();

    if (messageText === "") return;

    const userDiv = document.createElement("div");
    userDiv.className = "message user-msg";
    userDiv.innerText = messageText;
    chatHistory.appendChild(userDiv);
    inputField.value = "";
    chatHistory.scrollTop = chatHistory.scrollHeight;

    const aiDiv = document.createElement("div");
    aiDiv.className = "message ai-msg";
    aiDiv.innerText = "Đang xử lý...";
    chatHistory.appendChild(aiDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    try {
        const response = await fetch("https://manager-money.onrender.com/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: currentUsername, message: messageText })
        });

        const data = await response.json();
        chatHistory.removeChild(aiDiv);

        const resultDiv = document.createElement("div");
        resultDiv.className = "message ai-msg";
        resultDiv.innerText = data.reply;
        chatHistory.appendChild(resultDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        updateDashboard(data.so_du);
        renderHistory(data.history);

    } catch (error) {
        chatHistory.removeChild(aiDiv);
        alert("Lỗi kết nối!");
    }
}

function updateDashboard(soDu) {
    const tienMat = soDu.tien_mat;
    const tienTk = soDu.tien_tk;
    const tong = tienMat + tienTk;

    document.getElementById("tien-mat").innerText = tienMat.toLocaleString() + " đ";
    document.getElementById("tien-tk").innerText = tienTk.toLocaleString() + " đ";
    document.getElementById("tong-tien").innerText = tong.toLocaleString() + " đ";
}

function renderHistory(history) {
    const historyContainer = document.getElementById("history-list");
    historyContainer.innerHTML = "";

    if (!history || history.length === 0) {
        historyContainer.innerHTML = `<p style="color: #888; font-size: 13px; text-align: center;">Chưa có giao dịch nào.</p>`;
        return;
    }

    history.forEach(item => {
        const loai = item[0];
        const nguon = item[1] === "tien_mat" ? "Tiền mặt" : "Tiền TK";
        const tien = item[2].toLocaleString();
        const lyDo = item[3];

        const div = document.createElement("div");
        div.className = `history-item ${loai}`;
        div.innerHTML = `<strong>${loai === "thu" ? "THU" : "CHI"} (+${tien}đ / -${tien}đ)</strong><br>${lyDo} (${nguon})`;
        historyContainer.appendChild(div);
    });
}

function logout() {
    currentUsername = "";
    document.getElementById("logout-btn").style.display = "none";
    document.getElementById("auth-modal").style.display = "flex";
    document.getElementById("auth-user").value = "";
    document.getElementById("auth-pass").value = "";
    document.getElementById("chat-history").innerHTML = `<div class="message ai-msg">Chào bạn! Hãy nhập chi tiêu hôm nay.</div>`;
    document.getElementById("history-list").innerHTML = `<p style="color: #888; font-size: 13px; text-align: center;">Chưa có giao dịch nào.</p>`;
}

function handleKeyPress(event) {
    if (event.key === "Enter") sendMessage();
}
