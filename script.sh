Main_1() {
    unset ttttt complite2 ttttt2

    while true; do
        clear
        for f in {1..100}; do echo -e "\n"; done
        ttttt="${ttttt#*]}"
        clear
        echo "#################"
        [ -f "./TMP_CDEK_SCRIPT/complite.list" ] && {
            complite=$(cat ./TMP_CDEK_SCRIPT/complite.list)
        } || {
            echo -n "FFFFFFFFF" >./TMP_CDEK_SCRIPT/complite.list
        }
        case $ttttt in
        1)
            echo -e "$text_input" | grep -Ev "$complite" | awk '{print NR") Не просканированна - "$3" "$1}'
            ;;
        2)
            echo -e "$text_input" | grep -E "$complite" | awk '{print  NR") \033[1;4;90m\033[107mПросканированна\033[0m - "$3" "$1}'
            ;;
        4)
            [ -f "./TMP_CDEK_SCRIPT/complite.list" ] && {
                rm -f "./TMP_CDEK_SCRIPT/complite.list"
            }
            [ -f "./TMP_CDEK_SCRIPT/complite.list" ] && {
                complite=$(cat ./TMP_CDEK_SCRIPT/complite.list)
            } || {
                echo -n "FFFFFFFFF" >./TMP_CDEK_SCRIPT/complite.list
            }
            ;;
        3)
            echo "Выбери курьерв:"
            echo ""
            tick=1
            sel_num=""
            for x in $(echo -e "$text_input" | awk '{print $3}' | sort | uniq -d); do
                echo -e "$tick) $x [$(echo -e "$text_input" | awk '{print $3}' | grep $x | uniq -c | awk '{print $1}') ШТ]"
                sel_num="$sel_num\n$tick) $x"
                tick=$((tick + 1))
            done
            read sel_num2
            clear
            if ! (($sel_num2 > $tick)) && ! (($sel_num2 < 1)); then
                echo -e "$text_input" | grep -Ev "$complite" | grep "$(echo -e "$sel_num" | grep -w "$sel_num2)" | awk '{print $2}')" | awk '{print NR") Не просканированна - "$3" "$1}'
                echo -e "$text_input" | grep -E "$complite" | grep "$(echo -e "$sel_num" | grep -w "$sel_num2)" | awk '{print $2}')" | awk '{print  NR") \033[1;4;90m\033[107mПросканированна\033[0m - "$3" "$1}'
            fi
            ;;
        9)
            break
            ;;
        *)
            [ -n "$ttttt" ] && {
                if (($(echo -n $ttttt | wc -m) > 2)); then
                    echo -e "$text_input" | grep -q "$ttttt" && {
                        if (($(echo -e "$text_input" | grep "$ttttt" | wc -l) > 1)); then
                            ttttt2=$(echo -e "$text_input" | grep "$ttttt" | awk '{print $1}')
                            more_one=true
                        else
                            ttttt2=$ttttt
                            more_one=false
                        fi
                        tick2=1
                        for text_exp in $ttttt2; do
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
                            if (echo -e "$complite2" | grep -q "$text_exp"); then
                                echo " "
                                echo -e "Накладная: \033[30m\033[47m  $(echo -e "$text_input" | grep "$text_exp" | awk '{print $1}')  \033[0m уже сканировалась"
                            fi
                            if (($(echo -n $ttttt | wc -m) > 4)); then
                                echo -n "|$text_exp" >>./TMP_CDEK_SCRIPT/complite.list
                                complite2="$complite2\n$(echo -e "$text_input" | grep "$text_exp" | awk '{print $1}')\n$(echo -e "$text_input" | grep "$text_exp" | awk '{print $4}')"
                            fi

                        done
                    } || { echo "\n\n\n   Наклданая \"$ttttt\" не найдена"; }
                fi
            }
            ;;
        esac

        if [ -f "./TMP_CDEK_SCRIPT/Local_SHA_list" ] && [ -f "./TMP_CDEK_SCRIPT/cloud_SHA_list" ] && [ -n "$(cat ./TMP_CDEK_SCRIPT/cloud_SHA_list)" ]; then
            Local_list=$(
                cat ./TMP_CDEK_SCRIPT/Local_SHA_list
                rm -f ./TMP_CDEK_SCRIPT/Local_SHA_list
            )
            cloud_list=$(
                cat ./TMP_CDEK_SCRIPT/cloud_SHA_list
                rm -f ./TMP_CDEK_SCRIPT/cloud_SHA_list
            )
            [ "$Local_list" = "$cloud_list" ] || {
                sss="read"
                while ! [ -z "$sss" ]; do
                    clear
                    echo -e "  - Требуется обновления списка. Нажмите enter для продолжения"
                    echo "1:$Local_list"
                    echo "2:'$cloud_list'"
                    read sss
                done
                Read_text
            }
        fi
        echo "$date_now"
        echo -e "\n\n 1 - Для просмотра не просканнированных\n 2 - Для просмотра просканированных\n 3 - Для просмотра по курьерам ($cour_nam курьеров + $others)\n 4 - Удалить лист просканированных накладных\n 9 - Выход\n\n   Либо ввод любого другого числа для поиска\n\n"
        sha256sum ./TMP_CDEK_SCRIPT/list.txt | awk '{print $1}' >./TMP_CDEK_SCRIPT/Local_SHA_list
        curl -s https://master.dl.sourceforge.net/project/cdek-my/list.txt?viasf=1 | sha256sum | awk '{print $1}' >./TMP_CDEK_SCRIPT/cloud_SHA_list &
        read ttttt
    done
}
Update_script_check() {
    DOT=""
    tick=0
    cat "$0" | sha256sum | awk '{print $1}' >./TMP_CDEK_SCRIPT/Local_script
    curl -s https://master.dl.sourceforge.net/project/cdek-my/script.sh?viasf=1 | sha256sum | awk '{print $1}' >./TMP_CDEK_SCRIPT/cloud_script &
        while ps aux | grep -v grep | grep -qE "curl -s https://master.dl.sourceforge.net/project/cdek-my/script.sh?viasf=1|sha256sum|awk" &>/dev/null; do
            [ "$DOT" = "..." ] && {
                DOT=""
            } || {
                DOT+="."
            }
            clear
            echo "  - Проверка обновления скрипта в облаке$DOT"
            sleep 0.5
            tick=$((tick + 1))
            [ "$tick" = "120" ] && {
                clear
                echo -e "  - Время ожидание истекло\n  - Нажмите enter для выхода..."
                read
                exit 1
            }
        done
    wait
    clear
    Local_script=$(
        cat ./TMP_CDEK_SCRIPT/Local_script
        rm -f ./TMP_CDEK_SCRIPT/Local_script
    )
    cloud_script=$(
        cat ./TMP_CDEK_SCRIPT/cloud_script
        rm -f ./TMP_CDEK_SCRIPT/cloud_script
    )
    [ "$Local_script" = "$cloud_script" ] && {
        clear
        echo "  - Установлена свежая версия"
        sleep 2
    } || {
        clear
        echo -e "  - Требуется обновления скрипта. Нажмите enter для продолжения"
        read
        celar
        echo "  - Обновление скрипта..."
        curl -s https://master.dl.sourceforge.net/project/cdek-my/script.sh?viasf=1 >"$0"
        clear
        echo "  - Завершено! Перезапустите скрипт"
        exit 1

    }
}
Read_text() {
    DOT=""
    echo 1
        curl -s https://master.dl.sourceforge.net/project/cdek-my/list.txt?viasf=1 >./TMP_CDEK_SCRIPT/list.txt &
    sleep 0.1
    while ps aux | grep -v grep | grep 'curl -s https://master.dl.sourceforge.net/project/cdek-my/list.txt?viasf=1' ; do
        [ "$DOT" = "..." ] && {
            DOT=""
        } || {
            DOT+="."
        }
        clear
        echo "  - Загрузка списка подождите$DOT"
        sleep 0.5
    done
    wait
    text_input="$(cat ./TMP_CDEK_SCRIPT/list.txt | awk 'NR > 1 {print}')"
    cour_nam=0
    for x in $(echo -e "$text_input" | awk '{print $3}' | sort | uniq -d); do
        case $x in
        ПДЗ | пдз | Пдз | ПДз | ПдЗ | пДЗ | пдЗ | Отвал | ОТВАЛ | КБ3 | кб3 | ПВЗ | ГАЗ | Газ | газ)
            others+="$x,"
            ;;
        *)
            cour_nam=$((cour_nam + 1))
            ;;
        esac
    done
    date_now=$(cat ./TMP_CDEK_SCRIPT/list.txt | awk 'NR <= 1 {print}')
    others="${others%,*}"
}

[ -d TMP_CDEK_SCRIPT ] || mkdir -p TMP_CDEK_SCRIPT &>/dev/null
Update_script_check
Read_text
Main_1
