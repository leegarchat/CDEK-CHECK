

Main_1(){
    Read_text
    complite=FFFFFFFFF ; unset ttttt complite2 ttttt2
    cour_nam=0
    for x in $(echo -e "$text_input" | awk '{print $3}' | sort | uniq -d); do 
        case $x in
        ПДЗ|пдз|Пдз|ПДз|ПдЗ|пДЗ|пдЗ|Отвал|ОТВАЛ|КБ3|кб3|ПВЗ|ГАЗ|Газ|газ)
        others+="$x,"
        ;;
        *)
        cour_nam=$((cour_nam + 1))
        ;;
        esac
    done
    others="${others%,*}"
    while true ; do 
    clear ; for f in {1..100} ; do echo -e "\n" ; done ; ttttt="${ttttt#*]}" ; clear
    echo "#################"
    case $ttttt in
    1)
        echo -e "$text_input" | grep -Ev "$complite" | awk '{print NR") Не просканированна - "$3" "$1}'
    ;;
    2)
        echo -e "$text_input" | grep -E "$complite" | awk '{print  NR") \033[1;4;90m\033[107mПросканированна\033[0m - "$3" "$1}'
    ;;
    3)  
        echo "Выбери курьерв:"
        echo ""
        tick=1 ; sel_num=""
        for x in $(echo -e "$text_input" | awk '{print $3}' | sort | uniq -d); do echo -e "$tick) $x [$(echo -e "$text_input" | awk '{print $3}' | grep $x | uniq -c | awk '{print $1}') ШТ]" ; sel_num="$sel_num\n$tick) $x" ; tick=$((tick + 1))  ; done
        read sel_num2
        clear
        if ! (( $sel_num2 > $tick )) && ! (( $sel_num2 < 1 )) ; then  
        echo -e "$text_input" | grep -Ev "$complite" | grep "$(echo -e "$sel_num" | grep -w "$sel_num2)" | awk '{print $2}')" | awk '{print NR") Не просканированна - "$3" "$1}'
        echo -e "$text_input" | grep -E "$complite" | grep "$(echo -e "$sel_num" | grep -w "$sel_num2)" | awk '{print $2}')" | awk '{print  NR") \033[1;4;90m\033[107mПросканированна\033[0m - "$3" "$1}'
        fi
    ;;
    9)
    break
    ;;
    *)
    [ -n "$ttttt" ] && {
        if (( $(echo -n $ttttt | wc -m) > 2 )) ; then
            echo -e "$text_input" | grep -q "$ttttt" && {
                if (( $(echo -e "$text_input" | grep "$ttttt" | wc -l) > 1 )) ; then 
                    ttttt2=$(echo -e "$text_input" | grep "$ttttt" | awk '{print $1}') 
                    more_one=true
                else
                    ttttt2=$ttttt
                    more_one=false
                fi
                tick2=1
                for text_exp in $ttttt2 ; do
                    $more_one && {
                        echo " "
                        echo "$tick2-я найденая накладная:"
                        tick2=$((tick2 + 1))
                    }
                    echo "ШК место:"
                    echo -e "\033[1;4;90m\033[107m  $(echo -e "$text_input" | grep "$text_exp" | awk '{print $7}')  \033[0m"
                    echo "Номер накладной:"
                    echo -e "\033[1;4;90m\033[107m  $(echo -e "$text_input" | grep "$text_exp" | awk '{print $1}')  \033[0m"
                    echo "Курьер:"
                    echo -e "\033[1;4;90m\033[107m  $(echo -e "$text_input" | grep "$text_exp" | awk '{print $3}')  \033[0m"
                    echo -e "Всего доставок по списку:\033[1;4;90m\033[107m  $(echo -e "$text_input" | awk '{print $3}' | grep "$(echo -e "$text_input" | grep "$text_exp" | awk '{print $3}')" | uniq -c | awk '{print $1}')  \033[0m"
                    echo "Адрес:"
                    echo -e "\033[1;4;90m\033[107m  $(echo -e "$text_input" | grep "$text_exp" | awk '{print $5}')  \033[0m"
                    echo -e "Тариф:\n\033[1;4;90m\033[107m  $(echo -e "$text_input" | grep "$text_exp" | awk '{print $4}')  \033[0m"
                    echo -e "Макрозона:\033[1;4;90m\033[107m  $(echo -e "$text_input" | grep "$text_exp" | awk '{print $6}')  \033[0m"
                    echo -e "Вес по проге:\033[1;4;90m\033[107m  $(echo -e "$text_input" | grep "$text_exp" | awk '{print $2}')  \033[0m"
                    if ( echo -e "$complite2" | grep -q "$text_exp" ) ; then 
                        echo " "
                        echo -e "Накладная: \033[30m\033[47m  $(echo -e "$text_input" | grep "$text_exp" | awk '{print $1}')  \033[0m уже сканировалась"
                    fi
                    if (( $(echo -n $ttttt | wc -m) > 4 )) ; then
                        complite="$complite|$text_exp"
                        complite2="$complite2\n$(echo -e "$text_input" | grep "$text_exp" | awk '{print $1}')\n$(echo -e "$text_input" | grep "$text_exp" | awk '{print $4}')"
                    fi
                    
                done
            } || { echo "\n\n\n   Наклданая \"$ttttt\" не найдена" ; }
        fi
        } 
    ;;
    esac
    
    echo "Раскладка доставок до 12/14 на 09.03"
    echo -e "\n\n 1 - Для просмотра не просканнированных\n 2 - Для просмотра просканированных\n 3 - Для просмотра по курьерам ($cour_nam курьеров + $others)\n 9 - Выход\n\n   Либо ввод любого другого числа для поиска\n\n"
    read ttttt
    done
}
Read_text(){
text_input="1410711190	0.50	Балин	Супер-экспресс-до-12	ул-Будайская,-2	.2.07-КБ2	[ITM]000258844287
1410517270	0.50	Балин	Супер-экспресс-до-12	ЧИЧЕРИНА-УЛ,-12/2	.27.04-КБ2	[ITM]000258634829
1410543796	0.15	Балин	Супер-экспресс-до-14	ул-Новоалексеевская,-16-к2	.2.05-КБ2	[ITM]000258662273
1410633388	0.50	Булгаков	Супер-экспресс-до-12	пл-Триумфальная,-2,-строение-1	.9.06-КБ2	[ITM]000258759475
1410591950	0.30	Булгаков	Супер-экспресс-до-14	Большой-Гнездниковский-пер.,-7/6-стр.-1,2,--,--	.9.01-КБ2	[ITM]000258714419
1410595656	0.14	Булгаков	Супер-экспресс-до-14	Малый-Козихинский,-8/18	.9.06-КБ2	[ITM]000258718429
1410224614	0.20	Булгаков	Супер-экспресс-до-14	Трёхпрудный-пер,-9-стр-1,-кв-оф006	.9.06-КБ2	[ITM]000258319524
1410662207	0.20	Виноградова	Супер-экспресс-до-12	проезд-Лубянский,-11/1,	.12.05-КБ2	[ITM]000258790939
1410044097	0.20	Виноградова	Супер-экспресс-до-12	Покровский-бульвар11	.12.03-КБ2	[ITM]000258121001
1410466957	0.10	Виноградова	Супер-экспресс-до-12	ул-Охотный-Ряд,-1	.14.05-КБ2	[ITM]000258580930
1410548308	0.14	Виноградова	Супер-экспресс-до-14	Москва,-пер-Самотёчный-2-й,-7	.14.09-КБ2	[ITM]000258667089
1410650177	0.10	Виноградова	Супер-экспресс-до-14	Колокольников-пер,-д.-9,-стр.-2,-3-этаж	Сухаревская1	[ITM]000258777745
1410625524	0.50	Виноградова	Супер-экспресс-до-14	ул-Пушечная,-4,-строение-1	Сухаревская3	[ITM]000258750908
1410558971	0.50	Виноградова	Супер-экспресс-до-14	пл-Славянская,-4стр1,-210-окно-№1	.12.04-КБ2	[ITM]000258678440
1410665403	0.14	Виноградова	Супер-экспресс-до-14	ул-Гиляровского,-39	.14.04-КБ2	[ITM]000258794345
1410817146	1.00	Власов	Супер-экспресс-до-12	ул-Дыбенко,-7/1	.35.05-КБ2	[ITM]000258960694
1410764433	3.00	Власов	Супер-экспресс-до-14	пр-кт-Ленинградский,-31А,-строение-1	Хорошево2	[ITM]000258903159
1409376807	0.50	Власов	Супер-экспресс-до-14	г-Москва,-ул-Черняховского,-12	Масловка2	[ITM]000257401524
1410411805	16.00	ГАЗ	Супер-экспресс-до-12	Малый-Ивановский-переулок,-,-6стр2	.12.04-КБ2	[ITM]000258521743
1410591506	3.60	ГАЗ	Супер-экспресс-до-12	ул-Рочдельская,-15с11-11А	Декабрь-1	[ITM]000258713940
1410594948	3.60	ГАЗ	Супер-экспресс-до-12	ул-Рочдельская,-15с11-11А	Декабрь-1	[ITM]000258717680
1410581897	0.50	Дося-Курочкин	Супер-экспресс-до-12	пр-кт-Федеративный,-40к2	.36.02-КБ2	[ITM]000258703444
1410546031	1.20	Дося-Курочкин	Супер-экспресс-до-14	Краснопресненская-наб,-12	Живова-2	[ITM]000258664701
1410476043	0.50	Дося-Ломовцев	Супер-экспресс-до-12	наб.-Карамышевская,-62,-корпус-1	Живописная1	[ITM]000258590695
1410614176	0.50	Дося-Ломовцев	Супер-экспресс-до-12	ул-Лавочкина,-26	Шнейдер-Флот	[ITM]000258738546
1409835637	0.10	Дося-пеший-1	Супер-экспресс-до-12	пер-Просвирин,-4	Сухаревская2	[ITM]000257894403
1410583533	0.10	Дося-пеший-1	Супер-экспресс-до-12	Маши-Порываевой,-34	Красносельская2	[ITM]000258705200
1410565940	0.87	Дося-пеший-1	Супер-экспресс-до-12	КАЛАНЧЕВСКАЯ-УЛ,-27	.14.06-КБ2	[ITM]000258686058
1410823947	0.50	Дося-пеший-1	Супер-экспресс-до-14	ул-Красносельская-Верхн.,-2/1,-строение-2	Красносельская1	[ITM]000258968185
1410714326	0.50	Дося-пеший-1	Супер-экспресс-до-14	ул-Краснобогатырская,-2-стр-28	.18.06-КБ2	[ITM]000258847705
1409928741	0.50	Дося-пеший-1	Супер-экспресс-до-12	Маши-Порываевой,-34	Красносельская2	[ITM]000257996341
1410781371	0.50	Дося-Филянин	Супер-экспресс-до-12	ул-Яхромская,-3	Дмит-6	[ITM]000258921882
1410608948	0.50	Дося-Филянин	Супер-экспресс-до-14	проезд-Дмитровский,-10,-строение-3	.17.01-Кб2	[ITM]000258732813
1410658147	0.10	Кузнецов	Супер-экспресс-до-12	МАГИСТРАЛЬНЫЙ-ТУПИК-1,-11-стр1	.22.03-кб2	[ITM]000258786479
1410040167	0.65	Кузнецов	Супер-экспресс-до-12	ш-Хорошёвское,-32А	.22.04-кб2	[ITM]000258116698
20959037	0.50	Кузнецов	Супер-экспресс-до-12	Хорошевское-шоссе,-38	.22.04-кб2	[ITM]000258842973
1410732113	0.40	Лавров	Супер-экспресс-до-12	М-Семёновская-,-д-3а-К1	Преображенская2	[ITM]000258867268
1410638927	0.50	Лавров	Супер-экспресс-до-12	Проспект-Мира,-72	.14.06-КБ2	[ITM]000258765551
1410591779	4.80	Лавров	Супер-экспресс-до-12	Матросская-тишина,-23-стр.-1	.18.10-КБ2	[ITM]000258714238
1410594801	0.1	Митянин	Супер-экспресс-до-14	чаплыгина,-4,--	.12.04-КБ2	[ITM]000258717513
1409696083	1.20	Отвал	Супер-экспресс-до-12	г-Москва,-ш-Дмитровское,-д-107А-к-1	Дмит-5	[ITM]000257741985
1410568645	0.50	Панин	Супер-экспресс-до-12	пер-Лесной-4-й,-4	.14.01-КБ2	[ITM]000258689022
1410551250	0.50	Панин	Супер-экспресс-до-12	Дмитровское-шоссе,-71Б,-кв-оф630	Дмит-2	[ITM]000258670209
1410333310	0.50	Панин	Супер-экспресс-до-12	ул-Правды,-8-литер-кор1	.9.02-КБ2	[ITM]000258438970
1410674593	0.50	Потапов	Супер-экспресс-до-12	проезд-Красногвардейский-1-й,-башня-меркурий	Живова-2	[ITM]000258804418
1410566360	2.00	Потапов	Супер-экспресс-до-12	1-КРАСНОГВАРДЕЙСКИЙ-ПРОЕЗД,-21	.29.03-КБ2	[ITM]000258686549
1410620873	0.10	Потапов	Супер-экспресс-до-12	проезд-Красногвардейский-1-й,-21-стр.1	.29.03-КБ2	[ITM]000258745811
1410225168	0.10	Потапов	Супер-экспресс-до-12	наб-Пресненская,-Д.-10-блок-В	.29.04-КБ2	[ITM]000258320112
1410698802	0.53	Потапов	Супер-экспресс-до-14	наб-Пресненская,-8,-строение-1	.29.05-КБ2	[ITM]000258830671
1393798984	0.50	Потапов	Супер-экспресс-до-14	Шелепихинское-шоссе-д.25;,	Газ6-22.03-6	[ITM]000240499129
1410802710	0.50	Рыжов	Супер-экспресс-до-12	Улица-Земляной-Вал,,-35-с-1,-эт.-3	.12.07-КБ2	[ITM]000258945101
1408968031	2.00	Рыжов	Супер-экспресс-до-14	ВОЛОКОЛАМСКОЕ-Ш,-д.2	.8.07-кб2	[ITM]000256953746
1410592150	0.30	Семерня	Супер-экспресс-до-12	ул-Каретный-Ряд,-2	.14.07-КБ2	[ITM]000258714655
1410084151	0.50	Семерня	Супер-экспресс-до-14	Оружейный-переулок,-15А	.14.02-КБ2	[ITM]000258164909
1410631762	0.30	Семченко	Супер-экспресс-до-12	ул-Большая-Молчановка,-д.-30/7,-стр.-2	.29.10-КБ2	[ITM]000258757677
1410179007	0.10	Торосян	Супер-экспресс-до-12	ул-Песчаная-3-я,-2а	Хорошёвка-8	[ITM]000258269247
1410688201	0.52	Торосян	Супер-экспресс-до-12	б-р-Ходынский,-9	.22.06-кб2	[ITM]000258819050"
}

Main_1


