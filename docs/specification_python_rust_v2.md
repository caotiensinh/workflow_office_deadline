# Education_AI_Workflow_Python_Rust_Design_V2

> Text-preserving editable export from the project DOCX. The editable original is in docs/assets.

PROJECT DESIGN SPECIFICATION

## Education AI Workflow

Python + Rust  |  Automation-first  |  Human-in-the-loop

Thiết kế triển khai thay thế cách phụ thuộc Power Automate. Mục tiêu: giảm thao tác thủ công; kiểm tra, nhắc việc và cảnh báo tự động; chỉ yêu cầu con người khi cần xác minh, phê duyệt hoặc xử lý ngoại lệ.

## 1. Phạm vi và nguyên tắc

Python điều phối: thu thập dữ liệu, đọc DOCX/EML/Outlook Classic (tùy quyền), lưu SQLite, lịch chạy, gửi thông báo, audit.

Rust xử lý chính sách: quy tắc deadline, đủ căn cứ, trạng thái chờ phê duyệt; không truy cập dữ liệu thô hay mạng.

AI là module tùy chọn: không tự động gửi hồ sơ nhân sự/học sinh tới dịch vụ cloud. Chỉ kết nối nguồn và mô hình đã được tổ chức cho phép.

Con người xác nhận ngày hạn không rõ, căn cứ không đủ, quyết định nhân sự, gửi chính thức, phê duyệt hồ sơ; các bước còn lại tự động hóa theo luật.

## 2. Điều kiện triển khai

- Điều kiện | Thiết kế
- OS / runtime | Windows 10/11, Python 3.11+, Rust/Cargo đã được IT cho phép
- Không có admin | Chạy user-space, Task Scheduler; phải kiểm tra policy của IT
- Outlook Classic | Adapter Python COM đọc-only, cần pywin32 và Outlook đang đăng nhập
- New Outlook | Không dùng COM; cần Microsoft Graph delegated OAuth và consent
- Gửi cảnh báo | Local spool (bản thử) hoặc SMTP TLS cho người nhận cho phép
- Dữ liệu thật | Chỉ sau khi phê duyệt bảo mật, quyền truy cập, lưu giữ và RBAC

TRẠNG THÁI: Bản Python chạy thử đã PASS; Rust chưa biên dịch trong môi trường tạo tài liệu. Chưa tích hợp Outlook của khách hàng.

## 3. Kiến trúc module

- Tầng | Trách nhiệm | Thành phần
- Nguồn | Outlook, EML, Word, Excel và tài liệu | Outlook COM tùy chọn; EML/JSON, DOCX local
- Thu thập | Ẩn thông tin nhạy cảm, chuẩn hóa dữ liệu | Python intake adapter
- Orchestrator | Quản lý chu kỳ, điều phối nghiệp vụ | Python CLI + Task Scheduler
- Policy | Quy tắc sự kiện thuần xác định | Rust edu_rules binary
- State | Lưu phiên bản hồ sơ và bằng chứng | SQLite cases / audit / decisions
- Alert | Đệm thông báo, tránh trùng, lỗi gửi | SQLite outbox; SMTP/file dispatch
- Approval | Chỉ con người được phê duyệt | Local CLI hiện tại; SSO sản xuất sau
- AI review | Dự thảo trích xuất / ngôn ngữ | CHƯA TRIỂN KHAI; module tương lai

## 4. Luồng chạy mỗi chu kỳ

01  Đọc dữ liệu mới qua adapter được cho phép → kiểm tra phân loại.

02  Upsert theo định danh nguồn. Không được ghi đè quyết định của con người.

03  Python chuẩn hóa thời gian JST, cờ đã xác minh, tình trạng hồ sơ.

04  Gửi CASE records sang tiến trình Rust qua stdin; nhận EVENT records từ stdout.

05  Ghi thông báo idempotent vào SQLite; ẩn nhãn CONFIDENTIAL / RESTRICTED.

06  Gửi bản tin qua kênh đã cấu hình; lỗi SMTP bất định → UNKNOWN, không thử lại mù.

07  Nếu cần quyết định, đưa hồ sơ vào hàng chờ; xác thực và ghi audit phê duyệt.

08  Nếu được phê duyệt, trạng thái thay đổi; thực thi gửi mail / nộp hồ sơ vẫn là phase riêng sau nghiệm thu.

## 5. Giao tiếp Python ↔ Rust

Giao thức line/tab nội bộ, ID hồ sơ hex UTF-8 để tránh lỗi ký tự. Rust không được phép tự ghi DB hoặc truy cập dịch vụ ngoài.

CASE    hex_id    kind    class    status    days    due_state    expired    evidence    approval

EVENT    hex_id    rule_code    severity

Không có Rust binary hoặc engine lỗi: quá trình tick dừng và báo lỗi; không tự động âm thầm chuyển sang Python.

## 6. Các workflow nghiệp vụ

- ID | Mục tiêu | Tự động | Con người
- WF-01 | Email intake | Thu nhận an toàn, tạo case | Xác nhận ngày hạn mơ hồ
- WF-02 | Phân loại | Dựa trên dữ liệu có cấu trúc | Phân loại thông tin nhạy cảm chưa rõ
- WF-03 | Deadline | Đánh giá từng chu kỳ 15 phút | Xác nhận deadline chưa xác minh
- WF-04 | Reminder | Nhắc D−3, D−1, D0, quá hạn | Can thiệp khi quá hạn nghiêm trọng
- WF-05 | DOCX check | Kiểm tra mục bắt buộc và hash | Đọc, đánh giá nội dung thật
- WF-06 | Evidence/HR | Chặn thiếu evidence_ref | Quyết định nhân sự, đối chiếu luật
- WF-07 | Approval | Quản lý chờ duyệt và audit | Approve / Reject
- WF-08 | Recovery | Outbox, tránh gửi lặp | Xử lý kết quả SMTP UNKNOWN

## 7. Luật cảnh báo và điều kiện

- Kích hoạt | Kết quả / mức cảnh báo
- D−3 ngày | INFO: cần chuẩn bị
- D−1 ngày | WARNING: sắp đến hạn
- D0 | WARNING: hôm nay / đã quá hạn trong ngày
- D<0 | CRITICAL: quá hạn; đánh giá mỗi ngày
- Deadline chưa đủ căn cứ | WARNING: người phụ trách xác nhận
- Thiếu evidence_ref đối với HR / Regulation / Document | CRITICAL: HOLD, không cho duyệt
- READY_FOR_APPROVAL + đủ căn cứ | WARNING: yêu cầu quyết định người quản lý

Các mốc nhắc không bị phát lại nhiều lần trong cùng ngày và cùng revision. Nếu máy tính tắt vào D−3, hệ thống không thể tạo email quá khứ; khi khởi động lại sẽ đánh giá hạn hiện tại và báo quá hạn nếu có.

## 8. Mô hình trạng thái và an toàn

CASE: NEW → TRIAGE → DRAFT → READY_FOR_APPROVAL → APPROVED/REJECTED → COMPLETED. Bản v2 chỉ mở các thao tác cập nhật có kiểm soát, chưa có executor tự gửi hồ sơ.

- Dữ liệu | Quy tắc
- case_id / revision | Định danh duy nhất và chống phê duyệt phiên bản cũ
- due_at / due_verified | Dấu thời gian TZ-aware + xác minh do người thực hiện
- evidence_ref | Sự tồn tại của mã nguồn tài liệu, KHÔNG thay thế kiểm chứng pháp lý
- data_class | PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED
- approval_status | NOT_REQUIRED / PENDING / APPROVED / REJECTED
- alert_id | SHA-256(case_id, revision, rule, date) cho idempotency
- outbox.state | QUEUED / SENDING / SENT / UNKNOWN / STALE
- audit | Hành động / actor / timestamp / revision

## 9. Ranh giới phê duyệt

Không tự đánh giá, chấm điểm, xếp hạng giáo viên hoặc ra quyết định nhân sự.

Không tự gửi email chính thức, cập nhật lịch người khác hoặc nộp hồ sơ khi chưa có người duyệt.

Thiếu tài liệu căn cứ: báo “要確認”; không tự suy diễn theo kiến thức mô hình.

Bản demo chỉ xác thực tài khoản Windows bằng allowlist và xác nhận gõ thủ công. Production cần Entra ID/SSO, RBAC, MFA theo chính sách tổ chức.

## 10. Quy tắc bảo mật

Không lưu raw email/sender/subject trong intake; dữ liệu nhạy cảm xuất cảnh báo chỉ có ID và nhãn chung. Tài khoản và phân quyền NTFS, BitLocker, sao lưu, retention, Nhật ký và giám sát là những điều kiện chặn trước khi sử dụng dữ liệu thật.

## 11. Kiểm thử, nghiệm thu và triển khai

- Mức | Kết quả / bằng chứng
- Python unit / integration | 40/40 PASS; test_results.txt trong source kit
- CLI E2E Python | 5 case mẫu, tạo 6 thông báo; lặp lại 0 thông báo
- Outbox/file | 6 file JSON được tạo; chạy lại không phát lần hai
- Rust native compiler | CHƯA PASS: host không có rustc/cargo
- Windows Task Scheduler | CHƯA PASS: chưa có máy Windows được ủy quyền
- Outlook/SMTP/To Do | CHƯA PASS: chưa có kết nối/cấp quyền bên khách hàng
- AI pháp lý/nhân sự | CHƯA TRIỂN KHAI: chỉ có cổng chặn thiếu căn cứ

## 12. Lộ trình nghiệm thu trên Windows

GATE 1 — Build: cargo test, cargo build --release; đảm bảo binary không cần DLL bất thường.

GATE 2 — Integration: Python CLI gọi Rust thật; xác nhận 6 cảnh báo lần đầu và 0 khi chạy lặp.

GATE 3 — Scheduler: đăng ký task cho user thường; xác nhận run history, log, lần chạy định kỳ.

GATE 4 — Live intake: chỉ dùng mail giả lập đã được IT duyệt, kiểm tra Outlook Classic/Graph.

GATE 5 — Alert delivery: SMTP test đến allowlist, kiểm tra FAILED/UNKNOWN và đối soát trước retry.

GATE 6 — Pilot: chọn 3 nghiệp vụ, ghi thời gian trước/sau, tỉ lệ đúng, đánh giá bảo mật và rollback.

## 13. Quyết định thiết kế còn mở

Một số yêu cầu triển khai bắt buộc xác minh với cơ sở giáo dục: (1) Outlook Classic hay New Outlook, (2) chính sách cài Rust/Python và Task Scheduler, (3) thông báo bằng mail nội bộ hay local only, (4) người duyệt và SSO, (5) dữ liệu có được phép đi vào mô hình AI hay không.

Tài liệu kỹ thuật chi tiết, nguồn và checklist đầy đủ: xem README.md, docs/ARCHITECTURE.md, docs/STATUS.md trong bộ mã Python + Rust.
