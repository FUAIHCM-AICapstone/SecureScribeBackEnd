import React from 'react';
// Assuming FooterSection is available at this path as per user's request
import FooterSection from '@/components/landing/FooterSection';

const App = () => {
  return (
    <div className="min-h-screen bg-[var(--background-color)] font-sans text-gray-800">
      {/* Header */}
      <header className="bg-[var(--primary-color)] text-white p-6 shadow-md rounded-b-lg">
        <div className="container mx-auto text-center">
          <h1 className="text-3xl md:text-4xl font-bold">Điều khoản Dịch vụ</h1>
        </div>
      </header>

      {/* Main Content Area */}
      <main
        className="min-h-screen px-2 py-6 sm:px-6 md:px-10 lg:px-40"
        style={{
          background: 'var(--background-color)',
          color: 'var(--text-color)',
          fontFamily: 'var(--font-family-base)',
          fontSize: 'var(--font-size-base)',
          lineHeight: 'var(--line-height-base)',
        }}
      >
        {/* Render the terms of service content */}
        <div className="container mx-auto px-4 py-8">
          <h1 className="text-4xl font-bold text-[var(--primary-color)] mb-8 text-center">
            Điều khoản Dịch vụ của SecureScribe Meeting
          </h1>
          <p className="mb-6 text-[var(--text-color)] text-center">
            Cập nhật lần cuối: 25 tháng 7 năm 2025
          </p>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              1. Giới thiệu và Chấp thuận Điều khoản
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              Chào mừng bạn đến với SecureScribe Meeting! Các Điều khoản Dịch vụ này
              ("Điều khoản") cấu thành một thỏa thuận ràng buộc về mặt pháp lý
              giữa bạn và SecureScribe Meeting ("SecureScribe Meeting", "chúng tôi")
              quản lý việc bạn sử dụng các sản phẩm, dịch vụ, ứng dụng di động
              (nếu có) và trang web của chúng tôi (gọi chung là "Dịch vụ").
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Bằng cách nhấp vào nút "Tôi đồng ý" hoặc nút tương tự, đăng ký tài
              khoản, tải xuống ứng dụng hoặc bất kỳ bản nâng cấp ứng dụng nào,
              sử dụng ứng dụng trên thiết bị di động của bạn, hoặc truy cập hoặc
              sử dụng Dịch vụ, bạn xác nhận và đồng ý rằng bạn đã đọc, hiểu và
              đồng ý bị ràng buộc bởi các Điều khoản Dịch vụ này, cho dù bạn đã
              đăng ký với trang web hay ứng dụng hay chưa. Nếu bạn không đồng ý
              với các Điều khoản Dịch vụ này, bạn không có quyền truy cập hoặc
              sử dụng Dịch vụ.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Các Điều khoản Dịch vụ này có hiệu lực kể từ ngày bạn nhấp vào
              "Tôi đồng ý" (hoặc nút hoặc hộp kiểm tương tự) lần đầu tiên hoặc
              sử dụng hoặc truy cập Dịch vụ, tùy theo ngày nào sớm hơn.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Nếu bạn chấp nhận hoặc đồng ý với các Điều khoản Dịch vụ này thay
              mặt cho người sử dụng lao động của bạn hoặc một pháp nhân khác,
              bạn tuyên bố và đảm bảo rằng (i) bạn có đầy đủ thẩm quyền pháp lý
              để ràng buộc người sử dụng lao động của bạn hoặc pháp nhân đó với
              các Điều khoản Dịch vụ này; (ii) bạn đã đọc và hiểu các Điều khoản
              Dịch vụ này; và (iii) bạn đồng ý với các Điều khoản Dịch vụ này
              thay mặt cho bên mà bạn đại diện và bất kỳ người dùng được phép
              nào của bên đó. Trong trường hợp đó, "bạn" và "của bạn" sẽ đề cập
              và áp dụng cho người sử dụng lao động của bạn hoặc pháp nhân khác
              đó.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Bất kỳ dữ liệu cá nhân nào bạn gửi cho chúng tôi hoặc chúng tôi
              thu thập về bạn đều được điều chỉnh bởi Chính sách Bảo mật của
              chúng tôi ("Chính sách Bảo mật"). Bạn xác nhận rằng bằng cách sử
              dụng Dịch vụ, bạn đã xem xét Chính sách Bảo mật. Chính sách Bảo
              mật được tích hợp bằng cách tham chiếu vào các Điều khoản Dịch vụ
              này và cùng nhau tạo thành và sau đây được gọi là "Thỏa thuận"
              này.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Xin lưu ý: Thỏa thuận này quy định cách thức giải quyết tranh chấp
              giữa bạn và SecureScribe Meeting. Vui lòng đọc kỹ vì nó ảnh hưởng đến
              các quyền pháp lý của bạn.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Để sử dụng Dịch vụ của SecureScribe Meeting, bạn phải đủ 18 tuổi trở
              lên.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              2. Định nghĩa
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              Để đảm bảo sự rõ ràng trong các Điều khoản Dịch vụ này, các thuật
              ngữ sau đây được định nghĩa như sau:
            </p>
            <ul className="list-disc list-inside ml-4 text-[var(--text-color)]">
              <li className="mb-2">
                <strong>SecureScribe Meeting:</strong> Đề cập đến công ty cung cấp
                Dịch vụ, bao gồm các công ty con, chi nhánh, nhân viên và đại
                diện của nó.
              </li>
              <li className="mb-2">
                <strong>Dịch vụ:</strong> Định nghĩa toàn bộ phạm vi những gì
                SecureScribe Meeting cung cấp, bao gồm trang web https://SecureScribe
                Meeting/, phần mềm, các mô hình AI, tính năng, nội dung và bất
                kỳ sản phẩm hoặc ứng dụng liên quan nào.
              </li>
              <li className="mb-2">
                <strong>Người dùng:</strong> Bất kỳ cá nhân hoặc tổ chức nào
                truy cập hoặc sử dụng Dịch vụ.
              </li>
              <li className="mb-2">
                <strong>Tài khoản:</strong> Tài khoản đã đăng ký của người dùng
                với SecureScribe Meeting để truy cập và sử dụng các tính năng cụ thể
                của Dịch vụ.
              </li>
              <li className="mb-2">
                <strong>Nội dung:</strong> Bất kỳ văn bản, hình ảnh, âm thanh,
                video, dữ liệu hoặc tài liệu nào khác được SecureScribe Meeting cung
                cấp thông qua Dịch vụ.
              </li>
              <li className="mb-2">
                <strong>Dữ liệu Người dùng/Đầu vào:</strong> Bất kỳ dữ liệu,
                thông tin hoặc nội dung nào mà người dùng cung cấp, tải lên, gửi
                hoặc tạo ra thông qua Dịch vụ, đặc biệt là những dữ liệu tương
                tác với AI của SecureScribe Meeting, bao gồm ghi âm cuộc họp, bản
                ghi văn bản, và các tài liệu liên quan.
              </li>
              <li className="mb-2">
                <strong>Kết quả AI:</strong> Bất kỳ văn bản, hình ảnh, mã, phân
                tích hoặc tài liệu nào khác được tạo ra hoặc cung cấp bởi các mô
                hình AI của SecureScribe Meeting để phản hồi Dữ liệu Người dùng/Đầu
                vào, bao gồm ghi chú cuộc họp, bản ghi tự động và danh sách công
                việc được giao.
              </li>
              <li className="mb-2">
                <strong>Dữ liệu Cá nhân:</strong> Bất kỳ thông tin nào trực tiếp
                xác định một người hoặc khiến họ có thể được xác định khi kết
                hợp với thông tin khác từ hoặc về người đó từ bất kỳ nguồn nào.
              </li>
            </ul>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              3. Mô tả Dịch vụ SecureScribe Meeting
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              SecureScribe Meeting là một sản phẩm website được hỗ trợ bởi AI, được
              thiết kế để tự động ghi âm cuộc họp, ghi chú cuộc họp, ghi lại bản
              ghi, ghi lại các công việc được giao, là một công cụ quản lý cuộc
              họp, có tích hợp website để người dùng thao tác và xem lại lịch sử
              các cuộc họp đã được ghi chú. Phạm vi Dịch vụ bao gồm quyền truy
              cập vào trang web SecureScribe Meeting, các mô hình AI cơ bản, các
              tính năng liên quan, công cụ và bất kỳ tài liệu hoặc hỗ trợ liên
              quan nào.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              SecureScribe Meeting tích hợp với Google Meet, Zoom và Webex để cung
              cấp trải nghiệm ghi chú cuộc họp liền mạch.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              4. Tài khoản Người dùng
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              Để sử dụng Dịch vụ, bạn cần đăng ký với SecureScribe Meeting và tạo
              một tài khoản ("Tài khoản"). Trong quá trình đó, bạn sẽ được yêu
              cầu cung cấp một số thông tin nhất định, bao gồm tên và địa chỉ
              email của bạn. Bằng cách sử dụng Dịch vụ, bạn đồng ý cung cấp
              thông tin đúng, chính xác, hiện tại và đầy đủ theo yêu cầu của quy
              trình đăng ký và duy trì, cập nhật thông tin Tài khoản kịp thời để
              giữ cho thông tin đó chính xác, hiện tại và đầy đủ.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Bạn là người dùng được ủy quyền duy nhất của Tài khoản của mình.
              Bạn chịu trách nhiệm duy nhất trong việc duy trì tính bảo mật của
              bất kỳ thông tin đăng nhập, mật khẩu và số Tài khoản nào do bạn
              cung cấp hoặc do SecureScribe Meeting cấp cho bạn để truy cập Dịch vụ.
              Bạn hoàn toàn chịu trách nhiệm về tất cả các hoạt động xảy ra dưới
              mật khẩu hoặc Tài khoản của bạn. SecureScribe Meeting không kiểm soát
              việc sử dụng Tài khoản của bất kỳ người dùng nào và từ chối rõ
              ràng mọi trách nhiệm pháp lý phát sinh từ đó. Nếu bạn nghi ngờ
              rằng bất kỳ bên nào không được ủy quyền có thể đang sử dụng mật
              khẩu hoặc Tài khoản của bạn hoặc bạn nghi ngờ bất kỳ vi phạm bảo
              mật nào khác, bạn đồng ý liên hệ với SecureScribe Meeting ngay lập
              tức.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Người đăng ký Dịch vụ sẽ là bên ký hợp đồng ("Chủ Tài khoản") cho
              các mục đích của các Điều khoản Dịch vụ này và sẽ là người được ủy
              quyền sử dụng bất kỳ Tài khoản tương ứng nào chúng tôi cung cấp
              cho Chủ Tài khoản liên quan đến Dịch vụ; với điều kiện, nếu bạn
              đang đăng ký Dịch vụ thay mặt cho người sử dụng lao động của mình,
              người sử dụng lao động của bạn sẽ là Chủ Tài khoản. Là Chủ Tài
              khoản, bạn hoàn toàn chịu trách nhiệm tuân thủ các Điều khoản Dịch
              vụ này và chỉ bạn mới được hưởng tất cả các lợi ích phát sinh từ
              đó. Tài khoản của bạn không thể chuyển nhượng cho bất kỳ người
              hoặc tài khoản nào khác.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Bạn có thể hủy và xóa Tài khoản của mình bất cứ lúc nào bằng cách
              sử dụng các tính năng trên Dịch vụ để làm như vậy (nếu có và khả
              dụng) hoặc bằng cách thông báo bằng văn bản cho
              assistant.meowmo@gmail.com. Sau khi hủy, hồ sơ của bạn sẽ bị xóa
              và bạn sẽ không còn quyền truy cập vào Tài khoản, hồ sơ hoặc bất
              kỳ thông tin nào khác thông qua Dịch vụ.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              5. Quyền và Nghĩa vụ của Người dùng
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              SecureScribe Meeting cấp cho bạn quyền giới hạn, không độc quyền,
              không thể chuyển nhượng, có thể thu hồi tự do để truy cập và sử
              dụng Dịch vụ. Chúng tôi có thể chấm dứt quyền này bất cứ lúc nào
              vì bất kỳ lý do nào hoặc không có lý do.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Bạn đồng ý không tham gia vào bất kỳ hoạt động bị cấm nào sau đây,
              cùng với những hoạt động khác:
            </p>
            <ul className="list-disc list-inside ml-4 text-[var(--text-color)]">
              <li className="mb-2">
                Sao chép, phân phối hoặc tiết lộ bất kỳ phần nào của Dịch vụ
                bằng bất kỳ phương tiện nào khác ngoài những gì được cho phép
                bởi Dịch vụ và các Điều khoản Dịch vụ này.
              </li>
              <li className="mb-2">
                Sử dụng bất kỳ hệ thống tự động nào (ngoài bất kỳ chức năng nào
                của Dịch vụ), bao gồm nhưng không giới hạn ở "robot", "spider",
                "trình đọc ngoại tuyến", v.v., để truy cập Dịch vụ.
              </li>
              <li className="mb-2">
                Truyền tải thư rác, thư dây chuyền hoặc email không mong muốn
                khác hoặc cố gắng lừa đảo, tấn công mạng, giả mạo, thu thập dữ
                liệu, thu thập thông tin hoặc quét.
              </li>
              <li className="mb-2">
                Cố gắng can thiệp, xâm phạm tính toàn vẹn hoặc bảo mật hệ thống
                hoặc giải mã bất kỳ đường truyền nào đến hoặc từ các máy chủ
                đang chạy Dịch vụ.
              </li>
              <li className="mb-2">
                Vi phạm bất kỳ quy định, quy tắc, luật pháp hoặc pháp lệnh địa
                phương, quốc gia hoặc quốc tế nào.
              </li>
              <li className="mb-2">
                Thực hiện bất kỳ mục đích bất hợp pháp nào hoặc xúi giục người
                khác thực hiện hoặc tham gia vào bất kỳ hành vi bất hợp pháp
                nào.
              </li>
              <li className="mb-2">
                Tải lên dữ liệu không hợp lệ, virus, sâu máy tính hoặc các tác
                nhân phần mềm khác thông qua Dịch vụ.
              </li>
              <li className="mb-2">
                Xâm phạm hoặc vi phạm quyền sở hữu trí tuệ của chúng tôi hoặc
                quyền sở hữu trí tuệ của người khác.
              </li>
              <li className="mb-2">
                Mạo danh người khác hoặc xuyên tạc mối liên hệ của bạn với một
                người hoặc tổ chức, thực hiện gian lận, che giấu hoặc cố gắng
                che giấu danh tính của bạn.
              </li>
              <li className="mb-2">
                Quấy rối, lăng mạ, gây hại, lạm dụng, phỉ báng, quấy rối, rình
                rập, đe dọa, đe dọa hoặc vi phạm các quyền hợp pháp khác (như
                quyền riêng tư và công khai) của bất kỳ người dùng hoặc khách
                truy cập nào khác của Dịch vụ hoặc nhân viên của SecureScribe
                Meeting.
              </li>
              <li className="mb-2">
                Can thiệp hoặc bất kỳ hoạt động nào đe dọa hiệu suất, bảo mật
                hoặc chức năng hoạt động đúng đắn của Dịch vụ.
              </li>
              <li className="mb-2">
                Tải lên hoặc truyền tải virus hoặc bất kỳ loại mã độc hại nào
                khác.
              </li>
              <li className="mb-2">
                Cố gắng giải mã, dịch ngược, tháo rời hoặc đảo ngược kỹ thuật
                bất kỳ phần mềm hoặc thuật toán nào được sử dụng để cung cấp
                Dịch vụ.
              </li>
              <li className="mb-2">
                Bỏ qua các tính năng bảo mật hoặc biện pháp chúng tôi có thể sử
                dụng để ngăn chặn hoặc hạn chế quyền truy cập vào Dịch vụ, bao
                gồm nhưng không giới hạn ở các tính năng ngăn chặn hoặc hạn chế
                việc sử dụng hoặc sao chép bất kỳ nội dung nào hoặc thực thi các
                giới hạn về việc sử dụng Dịch vụ hoặc nội dung trong đó.
              </li>
              <li className="mb-2">
                Cố gắng truy cập các Tài khoản không được ủy quyền hoặc thu thập
                hoặc theo dõi thông tin cá nhân của người khác.
              </li>
              <li className="mb-2">
                Sử dụng Dịch vụ cho bất kỳ mục đích nào hoặc theo bất kỳ cách
                nào xâm phạm quyền của bất kỳ bên thứ ba nào.
              </li>
              <li className="mb-2">
                Khuyến khích hoặc cho phép bất kỳ cá nhân nào khác làm bất kỳ
                điều nào trong số những điều trên.
              </li>
            </ul>
            <p className="mb-4 text-[var(--text-color)]">
              Bạn chịu trách nhiệm tuân thủ tất cả các luật ghi âm. Bằng cách sử
              dụng Dịch vụ, bạn đồng ý cho SecureScribe Meeting lưu trữ các bản ghi
              cho bất kỳ hoặc tất cả các cuộc họp hoặc hội thảo trực tuyến của
              SecureScribe Meeting mà bạn tham gia, nếu các bản ghi đó được lưu trữ
              trong hệ thống của SecureScribe Meeting. Bạn sẽ nhận được thông báo
              (bằng hình ảnh hoặc cách khác) khi tính năng ghi âm được bật. Nếu
              bạn không đồng ý ghi âm, bạn có thể chọn rời khỏi cuộc họp.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              6. Quyền Sở hữu Trí tuệ
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              Tất cả văn bản, đồ họa, nội dung biên tập, dữ liệu, định dạng,
              biểu đồ, thiết kế, HTML, giao diện, hình ảnh, âm nhạc, âm thanh,
              hình ảnh, phần mềm, video, thiết kế, nhãn hiệu, logo, kiểu chữ và
              nội dung khác (gọi chung là "Tài liệu Độc quyền") mà người dùng
              nhìn thấy hoặc đọc thông qua Dịch vụ thuộc sở hữu của SecureScribe
              Meeting, không bao gồm Dữ liệu Người dùng/Đầu vào, mà người dùng
              cấp cho SecureScribe Meeting giấy phép sử dụng như được nêu trong đây.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              SecureScribe Meeting giữ tất cả các quyền, quyền sở hữu và lợi ích đối
              với Dịch vụ (bao gồm trang web, phần mềm, mô hình AI, thuật toán,
              công nghệ cơ bản và tất cả nội dung do SecureScribe Meeting cung cấp),
              tất cả các bản sao, chỉnh sửa, sửa đổi, cải tiến và tất cả các
              quyền sở hữu trí tuệ liên quan (bằng sáng chế, bản quyền, bí mật
              thương mại, nhãn hiệu, nhãn hiệu dịch vụ, lợi thế thương mại) và
              dữ liệu liên quan đến việc sử dụng của bạn.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Bạn giữ quyền sở hữu đối với Dữ liệu Người dùng/Đầu vào gốc của
              bạn được cung cấp cho Dịch vụ. Tuy nhiên, bạn cấp cho SecureScribe
              Meeting một giấy phép không độc quyền, toàn cầu, miễn phí bản
              quyền, có thể cấp phép lại và có thể chuyển nhượng để sử dụng, sao
              chép, sửa đổi, điều chỉnh, xuất bản, dịch, tạo các tác phẩm phái
              sinh từ, phân phối và hiển thị Dữ liệu Người dùng/Đầu vào cho mục
              đích vận hành, cải thiện và phát triển Dịch vụ, bao gồm việc đào
              tạo và tinh chỉnh các mô hình AI của SecureScribe Meeting.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Trong phạm vi pháp luật cho phép, bạn sở hữu Kết quả AI được tạo
              ra dựa trên Dữ liệu Người dùng/Đầu vào của bạn. Tuy nhiên, bạn cấp
              cho SecureScribe Meeting một giấy phép không độc quyền, toàn cầu, miễn
              phí bản quyền, có thể cấp phép lại và có thể chuyển nhượng để sử
              dụng, sao chép, sửa đổi, điều chỉnh, xuất bản, dịch, tạo các tác
              phẩm phái sinh từ, phân phối và hiển thị Kết quả AI cho mục đích
              cải thiện dịch vụ, đào tạo mô hình và các mục đích nội bộ.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Các nhãn hiệu dịch vụ và nhãn hiệu của SecureScribe Meeting, bao gồm
              nhưng không giới hạn ở logo SecureScribe Meeting, là nhãn hiệu dịch vụ
              thuộc sở hữu của SecureScribe Meeting. Bất kỳ nhãn hiệu, nhãn hiệu
              dịch vụ, logo và/hoặc tên thương mại nào khác xuất hiện thông qua
              Dịch vụ là tài sản của chủ sở hữu tương ứng. Bạn không được sao
              chép hoặc sử dụng bất kỳ nhãn hiệu, logo hoặc tên thương mại nào
              trong số này mà không có sự đồng ý trước bằng văn bản rõ ràng của
              chủ sở hữu.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Bạn có thể chọn hoặc chúng tôi có thể mời bạn gửi ý kiến, ý tưởng
              hoặc phản hồi về Dịch vụ, bao gồm nhưng không giới hạn ở cách cải
              thiện dịch vụ hoặc sản phẩm của chúng tôi ("Phản hồi"). Bằng cách
              gửi bất kỳ Phản hồi nào, bạn đồng ý rằng việc tiết lộ của bạn là
              miễn phí, không được yêu cầu và không bị hạn chế và sẽ không đặt
              SecureScribe Meeting dưới bất kỳ nghĩa vụ ủy thác hoặc nghĩa vụ nào
              khác, và chúng tôi được tự do sử dụng Phản hồi mà không phải bồi
              thường thêm cho bạn, và/hoặc tiết lộ Phản hồi trên cơ sở không bảo
              mật hoặc cách khác cho bất kỳ ai. Bạn cũng thừa nhận rằng, bằng
              cách chấp nhận việc gửi của bạn, SecureScribe Meeting không từ bỏ bất
              kỳ quyền nào để sử dụng Phản hồi tương tự hoặc liên quan đã được
              SecureScribe Meeting biết trước đó, được phát triển bởi nhân viên của
              mình hoặc thu được từ các nguồn khác ngoài bạn. Bạn thừa nhận rằng
              tất cả email và thư từ khác mà bạn gửi cho chúng tôi sẽ trở thành
              tài sản duy nhất và độc quyền của chúng tôi.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              7. Quyền riêng tư và Bảo vệ Dữ liệu
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              SecureScribe Meeting cam kết bảo vệ quyền riêng tư của bạn và xử lý Dữ
              liệu Cá nhân theo luật pháp hiện hành của Việt Nam và Chính sách
              Bảo mật của chúng tôi. Chính sách Bảo mật là một phần không thể
              thiếu của các Điều khoản này và điều chỉnh việc thu thập, sử dụng
              và tiết lộ Dữ liệu Cá nhân. Bạn được khuyến khích xem xét Chính
              sách Bảo mật để biết thông tin chi tiết.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Các loại thông tin được thu thập bao gồm:
            </p>
            <ul className="list-disc list-inside ml-4 text-[var(--text-color)]">
              <li className="mb-2">
                <strong>Thông tin do người dùng cung cấp:</strong> Thông tin
                được bạn cung cấp trực tiếp, bao gồm tên, địa chỉ email, tên
                công ty, chi tiết thanh toán, thông tin xác thực tài khoản, dữ
                liệu được cung cấp để sử dụng dịch vụ và đăng ký nhận bản tin.
              </li>
              <li className="mb-2">
                <strong>Thông tin được thu thập tự động:</strong> Dữ liệu kỹ
                thuật được thu thập tự động thông qua cookie, API, SDK và các
                công nghệ tương tự, bao gồm dữ liệu thiết bị, dữ liệu sử dụng và
                thông tin mạng/internet.
              </li>
              <li className="mb-2">
                <strong>Thông tin người dùng đăng trên Dịch vụ:</strong> Bất kỳ
                thông tin nào bạn tự nguyện công khai thông qua các tính năng
                cộng tác, bao gồm trò chuyện bằng giọng nói, video, văn bản,
                diễn đàn, bảng tin, hồ sơ công khai và hình đại diện.
              </li>
            </ul>
            <p className="mb-4 text-[var(--text-color)]">
              Thông tin được thu thập được sử dụng cho các mục đích như cung cấp
              dịch vụ, cá nhân hóa, liên lạc, cải thiện dịch vụ và tuân thủ pháp
              luật. Thông tin có thể được chia sẻ với bên thứ ba, bao gồm nhà
              cung cấp dịch vụ, cơ quan pháp lý và trong các sự kiện doanh
              nghiệp, theo các điều kiện nghiêm ngặt, với đầy đủ chi tiết trong
              Chính sách Bảo mật. SecureScribe Meeting cam kết bảo mật dữ liệu, sử
              dụng các công nghệ và quy trình bảo mật theo tiêu chuẩn ngành, bao
              gồm mã hóa dữ liệu khi lưu trữ và truyền tải, kiểm soát truy cập
              và kiểm toán bảo mật thường xuyên. SecureScribe Meeting cũng thực hiện
              các biện pháp cụ thể cho dữ liệu AI, bao gồm ẩn danh hóa/giả danh
              hóa dữ liệu để đào tạo mô hình và xử lý an toàn các đầu vào nhạy
              cảm.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              8. Tuyên bố Miễn trừ Trách nhiệm và Giới hạn Trách nhiệm
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              Các Dịch vụ được cung cấp trên cơ sở "nguyên trạng" và "có sẵn",
              không có bất kỳ bảo đảm nào, dù rõ ràng hay ngụ ý. SecureScribe
              Meeting từ chối tất cả các bảo đảm, bao gồm nhưng không giới hạn
              ở, các bảo đảm ngụ ý về khả năng bán được, sự phù hợp cho một mục
              đích cụ thể, không vi phạm và tính chính xác hoặc đầy đủ của Dịch
              vụ hoặc Kết quả AI.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              SecureScribe Meeting không đảm bảo tính chính xác, đầy đủ, độ tin cậy
              hoặc tính hữu ích của bất kỳ Kết quả AI nào được tạo ra bởi Dịch
              vụ. Bạn thừa nhận rằng Kết quả AI có thể chứa lỗi, sai lệch hoặc
              có thể không phù hợp cho tất cả các mục đích. Bạn chấp nhận mọi
              rủi ro liên quan đến việc sử dụng Kết quả AI.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              SecureScribe Meeting không đảm bảo quyền truy cập không bị gián đoạn,
              không có lỗi hoặc an toàn vào Dịch vụ. SecureScribe Meeting giới hạn
              trách nhiệm của mình đối với bất kỳ thiệt hại trực tiếp, gián
              tiếp, ngẫu nhiên, đặc biệt, do hậu quả hoặc trừng phạt nào, bao
              gồm nhưng không giới hạn ở mất lợi nhuận, dữ liệu, uy tín hoặc các
              tổn thất vô hình khác, phát sinh từ:
            </p>
            <ul className="list-disc list-inside ml-4 text-[var(--text-color)]">
              <li className="mb-2">
                Việc sử dụng hoặc không thể sử dụng Dịch vụ.
              </li>
              <li className="mb-2">
                Bất kỳ hành vi hoặc nội dung nào của bất kỳ bên thứ ba nào trên
                Dịch vụ.
              </li>
              <li className="mb-2">
                Bất kỳ nội dung nào thu được từ Dịch vụ, đặc biệt là Kết quả AI.
              </li>
              <li className="mb-2">
                Truy cập, sử dụng hoặc thay đổi trái phép các đường truyền hoặc
                nội dung.
              </li>
              <li className="mb-2">
                Các thiệt hại liên quan đến việc sử dụng hoặc dựa vào Kết quả
                AI.
              </li>
            </ul>
            <p className="mb-4 text-[var(--text-color)]">
              Trong mọi trường hợp, tổng trách nhiệm pháp lý tối đa của SecureScribe
              Meeting đối với tất cả các khiếu nại phát sinh từ hoặc liên quan
              đến các Điều khoản này hoặc việc sử dụng Dịch vụ sẽ không vượt quá
              số tiền bạn đã trả cho SecureScribe Meeting trong mười hai (12) tháng
              trước khi xảy ra sự kiện gây ra trách nhiệm pháp lý.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              9. Bồi thường
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              Bạn đồng ý bồi thường, bảo vệ và giữ cho SecureScribe Meeting, các chi
              nhánh, cán bộ, giám đốc, nhân viên và đại lý của họ không bị tổn
              hại từ bất kỳ và tất cả các khiếu nại, trách nhiệm pháp lý, thiệt
              hại, tổn thất, chi phí, chi phí hoặc phí (bao gồm phí luật sư hợp
              lý) phát sinh từ hoặc liên quan đến:
            </p>
            <ul className="list-disc list-inside ml-4 text-[var(--text-color)]">
              <li className="mb-2">Việc bạn truy cập hoặc sử dụng Dịch vụ.</li>
              <li className="mb-2">Việc bạn vi phạm các Điều khoản này.</li>
              <li className="mb-2">
                Việc bạn vi phạm bất kỳ quyền nào của bên thứ ba, bao gồm quyền
                sở hữu trí tuệ hoặc quyền riêng tư.
              </li>
              <li className="mb-2">
                Bất kỳ nội dung nào (Dữ liệu Người dùng/Đầu vào hoặc Kết quả AI)
                mà bạn tạo, tải lên hoặc phổ biến thông qua Dịch vụ, đặc biệt
                nếu nó gây hại, vi phạm quyền hoặc vi phạm pháp luật.
              </li>
              <li className="mb-2">
                Việc bạn dựa vào hoặc lạm dụng Kết quả AI.
              </li>
              <li className="mb-2">
                Sự cẩu thả hoặc hành vi sai trái cố ý của bạn.
              </li>
            </ul>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              10. Thay đổi Điều khoản
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              SecureScribe Meeting bảo lưu quyền, theo quyết định riêng của mình,
              sửa đổi hoặc thay thế các Điều khoản này bất cứ lúc nào. Các thay
              đổi sẽ có hiệu lực sau 10 ngày kể từ khi đăng các Điều khoản sửa
              đổi lên trang web hoặc thông báo cho bạn. SecureScribe Meeting sẽ cố
              gắng cung cấp thông báo hợp lý về bất kỳ thay đổi quan trọng nào
              thông qua email hoặc thông báo nổi bật trên trang web. Việc tiếp
              tục sử dụng Dịch vụ sau ngày có hiệu lực của các Điều khoản sửa
              đổi cấu thành sự chấp nhận của bạn đối với những thay đổi đó.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              11. Chấm dứt Dịch vụ
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              Bạn có thể chấm dứt tài khoản của mình bất cứ lúc nào bằng cách
              làm theo hướng dẫn được cung cấp trên Dịch vụ hoặc bằng cách liên
              hệ với SecureScribe Meeting. SecureScribe Meeting có thể tạm ngừng hoặc
              chấm dứt quyền truy cập của bạn vào tất cả hoặc bất kỳ phần nào
              của Dịch vụ bất cứ lúc nào, có hoặc không có lý do, có hoặc không
              có thông báo, có hiệu lực ngay lập tức, vì các lý do bao gồm nhưng
              không giới hạn ở:
            </p>
            <ul className="list-disc list-inside ml-4 text-[var(--text-color)]">
              <li className="mb-2">Vi phạm các Điều khoản này.</li>
              <li className="mb-2">Vi phạm luật pháp hiện hành.</li>
              <li className="mb-2">
                Hành vi gây hại cho người dùng khác, SecureScribe Meeting hoặc bên
                thứ ba.
              </li>
              <li className="mb-2">Không hoạt động.</li>
            </ul>
            <p className="mb-4 text-[var(--text-color)]">
              Khi chấm dứt, tất cả các quyền và giấy phép được cấp cho bạn sẽ
              ngay lập tức chấm dứt. Các điều khoản mà theo bản chất của chúng
              nên tồn tại sau khi chấm dứt (ví dụ: sở hữu trí tuệ, tuyên bố từ
              chối trách nhiệm, bồi thường, luật điều chỉnh) sẽ vẫn có hiệu lực.
              SecureScribe Meeting sẽ xóa tất cả dữ liệu của bạn, bao gồm mọi Dữ
              liệu Người dùng/Đầu vào, theo chính sách lưu giữ dữ liệu được nêu
              chi tiết trong Chính sách Bảo mật của chúng tôi.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              12. Luật Điều chỉnh và Giải quyết Tranh chấp
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              Các Điều khoản này sẽ được điều chỉnh và giải thích theo luật pháp
              của Cộng hòa Xã hội Chủ nghĩa Việt Nam, không tính đến các xung
              đột nguyên tắc pháp luật.
            </p>
            <p className="mb-4 text-[var(--text-color)]">
              Đối với giải quyết tranh chấp:
            </p>
            <ul className="list-disc list-inside ml-4 text-[var(--text-color)]">
              <li className="mb-2">
                <strong>Giải quyết không chính thức:</strong> Chúng tôi khuyến
                khích bạn liên hệ trực tiếp với SecureScribe Meeting qua email
                assistant.meowmo@gmail.com để giải quyết mọi tranh chấp một cách
                không chính thức trước khi tiến hành hành động pháp lý chính
                thức.
              </li>
              <li className="mb-2">
                <strong>Trọng tài ràng buộc:</strong> Bất kỳ tranh chấp, tranh
                cãi hoặc khiếu nại nào phát sinh từ hoặc liên quan đến các Điều
                khoản này hoặc việc sử dụng Dịch vụ, bao gồm cả sự tồn tại, hiệu
                lực, giải thích, thực hiện, vi phạm hoặc chấm dứt của chúng, sẽ
                được giải quyết bằng trọng tài tại Trung tâm Trọng tài Quốc tế
                Việt Nam (VIAC) theo Quy tắc Trọng tài của VIAC. Địa điểm trọng
                tài sẽ là Thành phố Hồ Chí Minh, Việt Nam. Ngôn ngữ của trọng
                tài sẽ là tiếng Việt. Quyết định của trọng tài sẽ là cuối cùng
                và ràng buộc đối với các bên.
              </li>
            </ul>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              13. Các Điều khoản Chung khác
            </h2>
            <ul className="list-disc list-inside ml-4 text-[var(--text-color)]">
              <li className="mb-2">
                <strong>Tính hiệu lực từng phần:</strong> Nếu bất kỳ điều khoản
                nào của các Điều khoản này được phát hiện là không thể thực thi
                hoặc không hợp lệ, điều khoản đó sẽ được giới hạn hoặc loại bỏ ở
                mức tối thiểu cần thiết, và các điều khoản còn lại sẽ vẫn có
                hiệu lực và đầy đủ.
              </li>
              <li className="mb-2">
                <strong>Từ bỏ quyền:</strong> Việc SecureScribe Meeting không thực
                thi bất kỳ quyền hoặc điều khoản nào của các Điều khoản này sẽ
                không được coi là sự từ bỏ các quyền đó.
              </li>
              <li className="mb-2">
                <strong>Toàn bộ thỏa thuận:</strong> Các Điều khoản này, cùng
                với Chính sách Bảo mật và bất kỳ thông báo pháp lý nào khác được
                SecureScribe Meeting công bố trên Dịch vụ, cấu thành toàn bộ thỏa
                thuận giữa SecureScribe Meeting và bạn liên quan đến Dịch vụ.
              </li>
              <li className="mb-2">
                <strong>Chuyển nhượng:</strong> Bạn không được chuyển nhượng
                hoặc chuyển giao các Điều khoản này, hoặc bất kỳ quyền hoặc
                nghĩa vụ nào theo đây, mà không có sự đồng ý trước bằng văn bản
                của SecureScribe Meeting. SecureScribe Meeting có thể chuyển nhượng các
                Điều khoản này mà không bị hạn chế.
              </li>
              <li className="mb-2">
                <strong>Bất khả kháng:</strong> SecureScribe Meeting sẽ không chịu
                trách nhiệm về bất kỳ sự chậm trễ hoặc thất bại nào trong việc
                thực hiện do các nguyên nhân nằm ngoài tầm kiểm soát hợp lý của
                mình, chẳng hạn như thiên tai, chiến tranh, khủng bố, bạo loạn,
                cấm vận, hành động của chính quyền dân sự hoặc quân sự, hỏa
                hoạn, lũ lụt, tai nạn, lỗi cơ sở hạ tầng mạng, đình công hoặc
                thiếu phương tiện vận chuyển, nhiên liệu, năng lượng, lao động
                hoặc vật liệu.
              </li>
              <li className="mb-2">
                <strong>Tiêu đề:</strong> Các tiêu đề được sử dụng trong các
                Điều khoản này chỉ mang tính chất thuận tiện và sẽ không ảnh
                hưởng đến việc giải thích chúng.
              </li>
            </ul>
          </section>

          <section className="mb-10">
            <h2 className="text-3xl font-semibold text-[var(--primary-color)] mb-4">
              14. Liên hệ
            </h2>
            <p className="mb-4 text-[var(--text-color)]">
              Để có bất kỳ câu hỏi hoặc thắc mắc nào liên quan đến các Điều
              khoản này, vui lòng liên hệ với SecureScribe Meeting qua địa chỉ
              email:{' '}
              <a
                href="mailto:assistant.meowmo@gmail.com"
                className="text-[var(--primary-color)] hover:underline"
              >
                assistant.meowmo@gmail.com
              </a>
              .
            </p>
          </section>
        </div>
      </main>

      {/* Footer (Placeholder - replace with actual FooterSection component if available) */}
      <FooterSection id="footer" />
      {/*  */}
    </div>
  );
};

export default App;
